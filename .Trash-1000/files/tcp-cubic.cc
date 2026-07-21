/* =============================================================
   tcp-cubic.cc  –  Scenario B : TCP Cubic
   Point-to-point network:  Sender ── link ── Receiver
   Outputs: tcp-cubic.pcap (on both nodes)
   ============================================================= */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("TcpCubicSimulation");

int main (int argc, char *argv[])
{
  // ── 1. Simulation parameters ──────────────────────────────
  double   simTime   = 20.0;
  uint32_t packetSize = 1024;
  std::string bandwidth = "1Mbps";
  std::string delay    = "10ms";
  uint32_t    queueSize = 10;

  CommandLine cmd;
  cmd.AddValue ("simTime",   "Simulation time (s)",  simTime);
  cmd.AddValue ("bandwidth", "Link bandwidth",        bandwidth);
  cmd.AddValue ("delay",     "Link delay",            delay);
  cmd.AddValue ("queueSize", "Queue size (packets)",  queueSize);
  cmd.Parse (argc, argv);

  // ── 2. Force TCP Cubic ────────────────────────────────────
  Config::SetDefault ("ns3::TcpL4Protocol::SocketType",
                      TypeIdValue (TcpCubic::GetTypeId ()));

  // ── 3. Create nodes ──────────────────────────────────────
  NodeContainer nodes;
  nodes.Create (2);

  // ── 4. Point-to-point link ───────────────────────────────
  PointToPointHelper p2p;
  p2p.SetDeviceAttribute  ("DataRate", StringValue (bandwidth));
  p2p.SetChannelAttribute ("Delay",    StringValue (delay));
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

  PacketSinkHelper sink ("ns3::TcpSocketFactory",
                         InetSocketAddress (Ipv4Address::GetAny (), port));
  ApplicationContainer sinkApp = sink.Install (nodes.Get (1));
  sinkApp.Start (Seconds (0.0));
  sinkApp.Stop  (Seconds (simTime));

  BulkSendHelper bulk ("ns3::TcpSocketFactory",
                       InetSocketAddress (ifaces.GetAddress (1), port));
  bulk.SetAttribute ("MaxBytes", UintegerValue (0));
  bulk.SetAttribute ("SendSize", UintegerValue (packetSize));
  ApplicationContainer senderApp = bulk.Install (nodes.Get (0));
  senderApp.Start (Seconds (1.0));
  senderApp.Stop  (Seconds (simTime));

  // ── 7. PCAP tracing ──────────────────────────────────────
  p2p.EnablePcapAll ("tcp-cubic");

  // ── 8. FlowMonitor ───────────────────────────────────────
  FlowMonitorHelper flowmon;
  Ptr<FlowMonitor> monitor = flowmon.InstallAll ();

  // ── 9. Run ───────────────────────────────────────────────
  NS_LOG_UNCOND ("Running TCP Cubic simulation for " << simTime << " seconds…");
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();

  // ── 10. Print flow stats ─────────────────────────────────
  monitor->CheckForLostPackets ();
  Ptr<Ipv4FlowClassifier> classifier =
      DynamicCast<Ipv4FlowClassifier> (flowmon.GetClassifier ());
  FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats ();

  NS_LOG_UNCOND ("\n===== TCP CUBIC – Flow Statistics =====");
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
  NS_LOG_UNCOND ("=======================================\n");

  Simulator::Destroy ();
  NS_LOG_UNCOND ("Done. PCAP files: tcp-cubic-0-0.pcap  tcp-cubic-1-0.pcap");
  return 0;
}
