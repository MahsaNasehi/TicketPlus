#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/error-model.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("TcpProject");

int main(int argc, char *argv[])
{
    // متغیر پیش‌فرض برای پروتکل
    std::string tcpVariant = "TcpReno";

    // دریافت متغیر از طریق خط فرمان
    CommandLine cmd(__FILE__);
    cmd.AddValue("tcpVariant", "Transport protocol to use: TcpReno, TcpCubic", tcpVariant);
    cmd.Parse(argc, argv);

    // تنظیم نوع پروتکل TCP بر اساس ورودی
    if (tcpVariant == "TcpReno") {
        Config::SetDefault("ns3::TcpL4Protocol::SocketType", StringValue("ns3::TcpReno"));
    } else if (tcpVariant == "TcpCubic") {
        Config::SetDefault("ns3::TcpL4Protocol::SocketType", StringValue("ns3::TcpCubic"));
    } else {
        NS_FATAL_ERROR("Invalid TCP variant specified. Use TcpReno or TcpCubic.");
    }

    // ۱. ایجاد گره‌های فرستنده و گیرنده
    NodeContainer nodes;
    nodes.Create(2);

    // ۲. تنظیم لینک نقطه-به-نقطه (Point-to-Point)
    PointToPointHelper pointToPoint;
    pointToPoint.SetDeviceAttribute("DataRate", StringValue("5Mbps"));
    pointToPoint.SetChannelAttribute("Delay", StringValue("2ms"));

    NetDeviceContainer devices;
    devices = pointToPoint.Install(nodes);

    // افزودن Error Model برای ایجاد دراپ مصنوعی (جهت مشاهده رفتار کنترل ازدحام)
    Ptr<RateErrorModel> em = CreateObject<RateErrorModel>();
    em->SetAttribute("ErrorRate", DoubleValue(0.00001));
    devices.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(em));

    // ۳. نصب پشته پروتکل اینترنت و تخصیص IP
    InternetStackHelper stack;
    stack.Install(nodes);

    Ipv4AddressHelper address;
    address.SetBase("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = address.Assign(devices);

    uint16_t port = 50000;

    // ۴. ایجاد برنامه گیرنده (Receiver / Sink) در گره ۱
    Address sinkLocalAddress(InetSocketAddress(Ipv4Address::GetAny(), port));
    PacketSinkHelper packetSinkHelper("ns3::TcpSocketFactory", sinkLocalAddress);
    ApplicationContainer sinkApps = packetSinkHelper.Install(nodes.Get(1));
    sinkApps.Start(Seconds(0.0));
    sinkApps.Stop(Seconds(10.0));

    // ۵. ایجاد برنامه فرستنده (Sender) در گره ۰
    AddressValue remoteAddress(InetSocketAddress(interfaces.GetAddress(1), port));
    BulkSendHelper ftp("ns3::TcpSocketFactory", Address());
    ftp.SetAttribute("Remote", remoteAddress);
    ftp.SetAttribute("SendSize", UintegerValue(1024));
    ftp.SetAttribute("MaxBytes", UintegerValue(0)); // ارسال نامحدود داده در زمان اجرا

    ApplicationContainer sourceApps = ftp.Install(nodes.Get(0));
    sourceApps.Start(Seconds(1.0));
    sourceApps.Stop(Seconds(10.0));

    // ۶. فعال‌سازی تولید فایل PCAP با نام‌گذاری پویا بر اساس نوع پروتکل
    pointToPoint.EnablePcapAll("tcp-project-" + tcpVariant);

    // ۷. اجرای شبیه‌سازی
    Simulator::Stop(Seconds(10.0));
    Simulator::Run();
    Simulator::Destroy();

    return 0;
}
