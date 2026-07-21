#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("TcpCompareProject");

int main (int argc, char *argv[])
{
  // تنظیم متغیر برای انتخاب نوع TCP (پیش‌فرض Reno)
  std::string tcpVariant = "TcpReno";
  
  CommandLine cmd;
  cmd.AddValue ("tcpVariant", "Transport protocol to use: TcpReno, TcpCubic", tcpVariant);
  cmd.Parse (argc, argv);

  // تنظیم نوع پروتکل TCP در ns-3
  if (tcpVariant == "TcpReno") {
      Config::SetDefault ("ns3::TcpL4Protocol::SocketType", TypeIdValue (TcpReno::GetTypeId ()));
  } else if (tcpVariant == "TcpCubic") {
      Config::SetDefault ("ns3::TcpL4Protocol::SocketType", TypeIdValue (TcpCubic::GetTypeId ()));
  } else {
      NS_FATAL_ERROR ("Invalid TCP variant selected!");
  }

  // ۱. ایجاد دو گره (فرستنده و گیرنده)
  NodeContainer nodes;
  nodes.Create (2);

  // ۲. تنظیم لینک Point-to-Point (پهنای باند و تاخیر)
  PointToPointHelper pointToPoint;
  pointToPoint.SetDeviceAttribute ("DataRate", StringValue ("5Mbps"));
  pointToPoint.SetChannelAttribute ("Delay", StringValue ("2ms"));

  NetDeviceContainer devices;
  devices = pointToPoint.Install (nodes);

  // ۳. نصب پشته اینترنت (TCP/IP) روی گره‌ها
  InternetStackHelper stack;
  stack.Install (nodes);

  // ۴. تخصیص آدرس IP
  Ipv4AddressHelper address;
  address.SetBase ("10.1.1.0", "255.255.255.0");
  Ipv4InterfaceContainer interfaces = address.Assign (devices);

  // ۵. ایجاد برنامه گیرنده (سرور) روی گره ۱
  uint16_t port = 8080;
  Address sinkAddress (InetSocketAddress (Ipv4Address::GetAny (), port));
  PacketSinkHelper packetSinkHelper ("ns3::TcpSocketFactory", sinkAddress);
  ApplicationContainer sinkApps = packetSinkHelper.Install (nodes.Get (1));
  sinkApps.Start (Seconds (1.0));
  sinkApps.Stop (Seconds (10.0));

  // ۶. ایجاد برنامه فرستنده (کلاینت) روی گره ۰
  BulkSendHelper source ("ns3::TcpSocketFactory", InetSocketAddress (interfaces.GetAddress (1), port));
  // مقدار داده‌ای که باید ارسال شود (۰ یعنی بی‌نهایت در زمان شبیه‌سازی)
  source.SetAttribute ("MaxBytes", UintegerValue (0));
  ApplicationContainer sourceApps = source.Install (nodes.Get (0));
  sourceApps.Start (Seconds (2.0));
  sourceApps.Stop (Seconds (10.0));

  // ۷. تولید فایل‌های PCAP
  // نام فایل PCAP بر اساس نوع TCP تغییر می‌کند تا تداخل ایجاد نشود
  pointToPoint.EnablePcapAll ("tcp-project-" + tcpVariant);

  // ۸. اجرای شبیه‌سازی
  Simulator::Stop (Seconds (10.0));
  Simulator::Run ();
  Simulator::Destroy ();

  return 0;
}
