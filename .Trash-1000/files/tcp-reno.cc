/* =============================================================
   tcp-reno.cc  –  Scenario A : TCP Reno
   Point-to-point network:  Sender ── link ── Receiver
   Outputs: tcp-reno.pcap (on both nodes)
   ============================================================= */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("TcpRenoSimulation");

int main (int argc, char *argv[])
{
  // ── 1. Simulation parameters ──────────────────────────────
  double   simTime   = 20.0;          // seconds
  uint32_t packetSize = 1024;         // bytes  (BulkSend uses segments)
  std::string bandwidth = "1Mbps";    // bottleneck bandwidth
  std::string delay    = "10ms";      // one-way propagation delay
  uint32_t    queueSize = 10;         // packets in DropTail queue  (bottleneck)

  CommandLine cmd;
  cmd.AddValue ("simTime",   "Simulation time (s)",  simTime);
  cmd.AddValue ("bandwidth", "Link bandwidth",        bandwidth);
  cmd.AddValue ("delay",     "Link delay",            delay);
  cmd.AddValue ("queueSize", "Queue size (packets)",  queueSize);
  cmd.Parse (argc, argv);

  // ── 2. Force TCP Reno ─────────────────────────────────────
  Config::SetDefault ("ns3::TcpL4Protocol::SocketType",
                      TypeIdValue (TcpNewReno::GetTypeId ()));

  // ── 3. Create nodes ──────────────────────────────────────
  NodeContainer nodes;
  nodes.Create (2);           // nodes[0] = sender, nodes[1] = receiver

  // ── 4. Point-to-point link ───────────────────────────────
  PointToPointHelper p2p;
  p2p.SetDeviceAttribute  ("DataRate", StringValue (bandwidth));
  p2p.SetChannelAttribute ("Delay",    StringValue (delay));
  // Bottleneck queue  (small queue → packet loss under congestion)
  p2p.SetQueue ("ns3::DropTailQueue",
                "MaxSize", StringValue (std::to_string (queueSize) + "p"));

  NetDeviceContainer devices = p2p.Install (nodes);

  // ── 5. Internet stack ─────────────────────────────────────
  InternetStackHelper internet;
  internet.Install (nodes);

  Ipv4AddressHelper ipv4;
  ipv4.SetBase ("10.1.1.0", "255.255.255.0");
  Ipv4InterfaceContainer ifaces = ipv4.Assign (devices);

  // ── 6. Applications ──────────────────────────────────────
  uint16_t port = 9;

  // --- Receiver: PacketSink ---
  PacketSinkHelper sink ("ns3::TcpSocketFactory",
                         InetSocketAddress (Ipv4Address::GetAny (), port));
  ApplicationContainer sinkApp = sink.Install (nodes.Get (1));
  sinkApp.Start (Seconds (0.0));
  sinkApp.Stop  (Seconds (simTime));

  // --- Sender: BulkSendApplication (fills pipe immediately) ---
  BulkSendHelper bulk ("ns3::TcpSocketFactory",
                       InetSocketAddress (ifaces.GetAddress (1), port));
  bulk.SetAttribute ("MaxBytes", UintegerValue (0));   // unlimited
  bulk.SetAttribute ("SendSize", UintegerValue (packetSize));
  ApplicationContainer senderApp = bulk.Install (nodes.Get (0));
  senderApp.Start (Seconds (1.0));
  senderApp.Stop  (Seconds (simTime));

  // ── 7. PCAP tracing ──────────────────────────────────────
  // Creates:  tcp-reno-0-0.pcap  (sender NIC)
  //           tcp-reno-1-0.pcap  (receiver NIC)
  p2p.EnablePcapAll ("tcp-reno");

  // ── 8. FlowMonitor (optional throughput log) ─────────────
  FlowMonitorHelper flowmon;
  Ptr<FlowMonitor> monitor = flowmon.InstallAll ();

  // ── 9. Run ───────────────────────────────────────────────
  NS_LOG_UNCOND ("Running TCP Reno simulation for " << simTime << " seconds…");
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();

  // ── 10. Print flow stats ─────────────────────────────────
  monitor->CheckForLostPackets ();
  Ptr<Ipv4FlowClassifier> classifier =
      DynamicCast<Ipv4FlowClassifier> (flowmon.GetClassifier ());
  FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats ();

  NS_LOG_UNCOND ("\n===== TCP RENO – Flow Statistics =====");
  for (auto &fs : stats)
    {
      Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow (fs.first);
      NS_LOG_UNCOND ("Flow " << fs.first
        << "  " << t.sourceAddress << " → " << t.destinationAddress);
      NS_LOG_UNCOND ("  Tx packets : " << fs.second.txPackets);
      NS_LOG_UNCOND ("  Rx packets : " << fs.second.rxPackets);
      NS_LOG_UNCOND ("  Lost pkts  : " << fs.second.lostPackets);
      double duration = fs.second.timeLastRxPacket.GetSeconds ()
                      - fs.second.timeFirstTxPacket.GetSeconds ();
      if (duration > 0)
        {
          double throughput = fs.second.rxBytes * 8.0 / duration / 1e6;
          NS_LOG_UNCOND ("  Throughput : " << throughput << " Mbps");
        }
    }
  NS_LOG_UNCOND ("======================================\n");

  Simulator::Destroy ();
  NS_LOG_UNCOND ("Done. PCAP files: tcp-reno-0-0.pcap  tcp-reno-1-0.pcap");
  return 0;
}
