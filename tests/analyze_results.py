import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

RESULTS_DIR = "./results"
OUTPUT_DIR = "./graphs"

def load_all_results():
    all_data = []
    if not os.path.exists(RESULTS_DIR):
        return pd.DataFrame()

    for f in os.listdir(RESULTS_DIR):
        if not f.endswith("_stats.csv"):
            continue

        parts = f.replace("_stats.csv", "").split("_c")
        if len(parts) != 2:
            continue
        
        name_parts = parts[0].split("-")
        func_name = "-".join(name_parts[:-1])
        mem_size = int(name_parts[-1])
        concurrency = int(parts[1])

        df = pd.read_csv(os.path.join(RESULTS_DIR, f))

        agg = df[df["Name"] != "Aggregated"]
        if agg.empty:
            agg = df

        row = df.iloc[-1]

        all_data.append({
            "function": func_name,
            "memory_mb": mem_size,
            "concurrency": concurrency,
            "avg_response_time": row.get("Average Response Time", 0),
            "median_response_time": row.get("Median Response Time", 0),
            "p95": row.get("95%", row.get("95% Response Time", 0)),
            "p99": row.get("99%", row.get("99% Response Time", 0)),
            "requests_per_sec": row.get("Requests/s", 0),
            "failure_rate": row.get("Failure Rate", row.get("Failure Count", 0)),
            "total_requests": row.get("Request Count", row.get("# Requests", 0)),
        })

    return pd.DataFrame(all_data)

def plot_response_vs_concurrency(df):
    functions = df["function"].unique()
    memory_sizes = sorted(df["memory_mb"].unique())

    fig, axes = plt.subplots(1, len(functions), figsize=(7 * len(functions), 5), squeeze=False)

    colors = {128: "#2196F3", 512: "#FF9800", 1024: "#4CAF50"}

    for i, func in enumerate(functions):
        ax = axes[0][i]
        func_data = df[df["function"] == func]

        for mem in memory_sizes:
            mem_data = func_data[func_data["memory_mb"] == mem].sort_values("concurrency")
            color = colors.get(mem, "#999")

            ax.plot(mem_data["concurrency"], mem_data["avg_response_time"],
                    "o-", color=color, label=f"{mem}MB (mean)", linewidth=2)
            ax.plot(mem_data["concurrency"], mem_data["p95"],
                    "s--", color=color, label=f"{mem}MB (p95)", alpha=0.7)
            ax.plot(mem_data["concurrency"], mem_data["p99"],
                    "^:", color=color, label=f"{mem}MB (p99)", alpha=0.5)

        ax.set_xlabel("Concurrency Level")
        ax.set_ylabel("Response Time (ms)")
        ax.set_title(f"Response Time vs Concurrency\n({func})")
        ax.set_xticks(sorted(func_data["concurrency"].unique()))
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "response_vs_concurrency.png"), dpi=150)
    plt.close()
    print("saved: response_vs_concurrency.png")

def plot_throughput_vs_concurrency(df):
    functions = df["function"].unique()
    memory_sizes = sorted(df["memory_mb"].unique())

    fig, axes = plt.subplots(1, len(functions), figsize=(7 * len(functions), 5), squeeze=False)

    colors = {128: "#2196F3", 512: "#FF9800", 1024: "#4CAF50"}

    for i, func in enumerate(functions):
        ax = axes[0][i]
        func_data = df[df["function"] == func]

        for mem in memory_sizes:
            mem_data = func_data[func_data["memory_mb"] == mem].sort_values("concurrency")
            color = colors.get(mem, "#999")

            ax.plot(mem_data["concurrency"], mem_data["requests_per_sec"],
                    "o-", color=color, label=f"{mem}MB", linewidth=2)

        ax.set_xlabel("Concurrency Level")
        ax.set_ylabel("Throughput (req/s)")
        ax.set_title(f"Throughput vs Concurrency\n({func})")
        ax.set_xticks(sorted(func_data["concurrency"].unique()))
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "throughput_vs_concurrency.png"), dpi=150)
    plt.close()
    print("saved: throughput_vs_concurrency.png")

def plot_burst_vs_steady(df):
    burst_data = df[df["function"].str.contains("burst", case=False) | df["function"].str.contains("steady", case=False)]
    if burst_data.empty:
        return

    labels = ["Steady State", "Burst Load"]
    avg_rt = []
    p95_rt = []
    p99_rt = []

    for label in ["steady", "burst"]:
        row = df[df["function"].str.contains(label, case=False)]
        if not row.empty:
            r = row.iloc[0]
            avg_rt.append(r["avg_response_time"])
            p95_rt.append(r["p95"])
            p99_rt.append(r["p99"])
        else:
            avg_rt.append(0)
            p95_rt.append(0)
            p99_rt.append(0)

    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.bar(x - width, avg_rt, width, label="Avg", color="steelblue")
    ax.bar(x, p95_rt, width, label="p95", color="orange")
    ax.bar(x + width, p99_rt, width, label="p99", color="tomato")

    ax.set_title("Objective 2: Steady vs Burst Invocation Pattern")
    ax.set_ylabel("Response Time (ms)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "burst_vs_steady.png"), dpi=150)
    plt.close()
    print("saved: burst_vs_steady.png")

def print_summary_table(df):
    cols = ["function", "memory_mb", "concurrency", "avg_response_time",
            "median_response_time", "p95", "p99", "requests_per_sec", "total_requests"]
    summary = df[cols].sort_values(["function", "memory_mb", "concurrency"])
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(summary.to_string(index=False))
    summary.to_csv(os.path.join(OUTPUT_DIR, "summary_table.csv"), index=False)

if __name__ == "__main__":
    import numpy as np
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df = load_all_results()

    if df.empty:
        print("no results found")
        exit(1)

    plot_response_vs_concurrency(df)
    plot_throughput_vs_concurrency(df)
    plot_burst_vs_steady(df)
    print_summary_table(df)

