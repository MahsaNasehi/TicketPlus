import os
import time
import json
import subprocess
import statistics
import csv
import matplotlib.pyplot as plt

# =======================
# Configuration
# =======================

BW_LIMIT = "10mbit"
RTTS = ["10ms", "50ms", "100ms", "200ms"]
ALGORITHMS = ["cubic", "bbr"]
INTERFACE = "lo"
PORT = 5201
DURATION = 10
RUNS_PER_TEST = 3
PACKET_LOSS = "0.5%"   # اگر نمی‌خواهی loss داشته باشی بگذار None

# =======================

def setup_tc(rtt):
    print(f"\nSetting up tc for RTT {rtt} | BW {BW_LIMIT}")

    os.system(f"tc qdisc del dev {INTERFACE} root 2>/dev/null")

    # Bandwidth limit
    os.system(
        f"tc qdisc add dev {INTERFACE} root handle 1: "
        f"tbf rate {BW_LIMIT} burst 100kbit limit 2mb"
    )

    delay = int(rtt.replace("ms", "")) // 2

    netem_cmd = (
        f"tc qdisc add dev {INTERFACE} parent 1: handle 10: "
        f"netem delay {delay}ms"
    )

    if PACKET_LOSS:
        netem_cmd += f" loss {PACKET_LOSS}"

    os.system(netem_cmd)


def clear_tc():
    os.system(f"tc qdisc del dev {INTERFACE} root 2>/dev/null")


def run_iperf(algo):
    cmd = [
        "iperf3", "-c", "127.0.0.1",
        "-p", str(PORT),
        "-C", algo,
        "-t", str(DURATION),
        "-J"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        data = json.loads(result.stdout)

        throughput = data["end"]["sum_sent"]["bits_per_second"] / 1e6

        # مسیر صحیح retransmits
        retransmits = data["end"]["streams"][0]["sender"].get("retransmits", 0)

        return throughput, retransmits

    except Exception as e:
        print(f"Error parsing JSON for {algo}: {e}")
        return 0, 0


# =======================
# Main
# =======================

def main():
    if os.geteuid() != 0:
        print("Run with sudo.")
        exit(1)

    results_throughput = {algo: [] for algo in ALGORITHMS}
    results_retransmits = {algo: [] for algo in ALGORITHMS}

    print("Starting iperf3 server...")
    server = subprocess.Popen(
        ["iperf3", "-s", "-p", str(PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(2)

    try:
        for rtt in RTTS:
            setup_tc(rtt)

            for algo in ALGORITHMS:
                tputs = []
                retxs = []

                print(f"\nTesting {algo.upper()} @ {rtt}")

                for _ in range(RUNS_PER_TEST):
                    tput, retx = run_iperf(algo)
                    tputs.append(tput)
                    retxs.append(retx)

                avg_tput = statistics.mean(tputs)
                avg_retx = statistics.mean(retxs)

                results_throughput[algo].append(avg_tput)
                results_retransmits[algo].append(avg_retx)

                print(f"  Avg Throughput: {avg_tput:.2f} Mbps")
                print(f"  Avg Retransmits: {avg_retx:.2f}")

            clear_tc()

    finally:
        clear_tc()
        server.terminate()

    # =======================
    # Save CSV
    # =======================

    with open("results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["RTT", "Algorithm", "Throughput(Mbps)", "Retransmits"])

        for i, rtt in enumerate(RTTS):
            for algo in ALGORITHMS:
                writer.writerow([
                    rtt,
                    algo,
                    results_throughput[algo][i],
                    results_retransmits[algo][i]
                ])

    # =======================
    # Plot
    # =======================

    x = range(len(RTTS))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Throughput
    ax1.bar([i - width/2 for i in x],
            results_throughput["cubic"],
            width, label="Cubic")

    ax1.bar([i + width/2 for i in x],
            results_throughput["bbr"],
            width, label="BBR")

    ax1.set_ylabel("Throughput (Mbps)")
    ax1.set_title(f"Throughput vs RTT (BW={BW_LIMIT}, Loss={PACKET_LOSS})")
    ax1.set_xticks(x)
    ax1.set_xticklabels(RTTS)
    ax1.legend()

    # Retransmissions
    ax2.bar([i - width/2 for i in x],
            results_retransmits["cubic"],
            width, label="Cubic")

    ax2.bar([i + width/2 for i in x],
            results_retransmits["bbr"],
            width, label="BBR")

    ax2.set_ylabel("Retransmissions")
    ax2.set_title("Retransmissions vs RTT")
    ax2.set_xticks(x)
    ax2.set_xticklabels(RTTS)
    ax2.legend()

    plt.tight_layout()
    plt.savefig("results.png")
    print("\n✅ Done. Saved: results.png & results.csv")


if __name__ == "__main__":
    main()
