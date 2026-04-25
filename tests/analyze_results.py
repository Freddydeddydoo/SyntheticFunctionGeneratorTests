import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")

RESULTS_DIR = "./results"
OUTPUT_DIR = "./graphs"

STEM_RE = re.compile(
    r"^(?:(steady|burst)_)?(.+)-(\d+)(?:_c(\d+))?(?:_r(low|med|high))?$"
)


def parse_stem(stem: str):
    m = STEM_RE.match(stem)
    if not m:
        return None
    raw_pat, func_base, mem_s, conc_s, rate = m.groups()
    if raw_pat == "burst":
        load_pattern = "burst"
    elif raw_pat == "steady":
        load_pattern = "steady"
    else:
        load_pattern = "steady" if conc_s else "legacy"
    rate_norm = rate if rate else "med"
    return {
        "load_pattern": load_pattern,
        "function": func_base,
        "memory_mb": int(mem_s),
        "concurrency": int(conc_s) if conc_s else None,
        "rate": rate_norm,
    }


def calculate_stats_from_history(history_file: str) -> dict:
    if not os.path.exists(history_file):
        return {}
    
    try:
        df = pd.read_csv(history_file)
        agg = df[df["Name"] == "Aggregated"].copy()
        if agg.empty:
            agg = df[df["Type"] == "lambda"].copy()
        
        if agg.empty or len(agg) < 2:
            return {}
        
        avg_col = "Total Average Response Time"
        if avg_col not in agg.columns:
            return {}
        
        valid = agg[agg[avg_col] > 0].copy()
        if len(valid) < 2:
            return {}
        
        response_times = valid[avg_col].values

        n = len(response_times)
        _ = response_times[-1]

        median_col = "50%"
        if median_col in valid.columns:
            medians = valid[median_col].replace("N/A", np.nan).astype(float).dropna()
            if len(medians) > 1:
                std_rt = medians.std()
                sem = std_rt / np.sqrt(len(medians))
                ci_95 = 1.96 * sem
            else:
                std_rt = 0
                ci_95 = 0
        else:
            std_rt = 0
            ci_95 = 0
        
        return {
            "std_response_time": std_rt,
            "ci_95": ci_95,
            "sample_count": n,
        }
    except Exception as e:
        print(f"warning: could not parse {history_file}: {e}")
        return {}


def load_all_results():
    all_data = []
    if not os.path.exists(RESULTS_DIR):
        return pd.DataFrame()

    for f in os.listdir(RESULTS_DIR):
        if not f.endswith("_stats.csv"):
            continue
        stem = f.replace("_stats.csv", "")
        meta = parse_stem(stem)
        if not meta:
            continue

        stats_file = os.path.join(RESULTS_DIR, f)
        history_file = os.path.join(RESULTS_DIR, f.replace("_stats.csv", "_stats_history.csv"))
        
        df = pd.read_csv(stats_file)
        agg_rows = df[df["Type"] != "lambda"]
        if not agg_rows.empty:
            row = agg_rows.iloc[-1]
        else:
            row = df.iloc[-1]

        history_stats = calculate_stats_from_history(history_file)

        std_rt = history_stats.get("std_response_time", 0)
        ci_95 = history_stats.get("ci_95", 0)
        sample_count = history_stats.get("sample_count", 0)

        if std_rt == 0:
            p50 = row.get("50%", row.get("Median Response Time", 0))
            p95 = row.get("95%", 0)
            if p95 > 0 and p50 > 0:
                std_rt = (p95 - p50) / 1.645
                n = row.get("Request Count", row.get("# Requests", 30))
                if n > 0:
                    ci_95 = 1.96 * std_rt / np.sqrt(n)

        all_data.append(
            {
                **meta,
                "avg_response_time": row.get("Average Response Time", 0),
                "median_response_time": row.get("Median Response Time", row.get("50%", 0)),
                "std_response_time": std_rt,
                "ci_95": ci_95,
                "p95": row.get("95%", row.get("95% Response Time", 0)),
                "p99": row.get("99%", row.get("99% Response Time", 0)),
                "min_response_time": row.get("Min Response Time", 0),
                "max_response_time": row.get("Max Response Time", 0),
                "requests_per_sec": row.get("Requests/s", 0),
                "failure_count": row.get("Failure Count", 0),
                "total_requests": row.get("Request Count", row.get("# Requests", 0)),
                "sample_count": sample_count if sample_count > 0 else row.get("Request Count", row.get("# Requests", 0)),
                "source_file": f,
            }
        )

    return pd.DataFrame(all_data)


def _filter_steady_for_concurrency_plots(df: pd.DataFrame, rate: str) -> pd.DataFrame:
    d = df[df["load_pattern"] != "burst"].copy()
    d["rate"] = d["rate"].fillna("med")
    return d[d["rate"] == rate]


def plot_response_vs_concurrency(df, rate: str):
    d = _filter_steady_for_concurrency_plots(df, rate)
    if d.empty:
        print(f"skipping response_vs_concurrency, no steady rows for rate={rate}")
        return

    functions = sorted(d["function"].unique())
    memory_sizes = sorted(d["memory_mb"].unique())
    if not functions:
        return

    fig, axes = plt.subplots(1, len(functions), figsize=(7 * len(functions), 6), squeeze=False)
    colors = {128: "#2196F3", 512: "#FF9800", 1024: "#4CAF50"}

    for i, func in enumerate(functions):
        ax = axes[0][i]
        func_data = d[d["function"] == func]
        if func_data.empty:
            continue
        for mem in memory_sizes:
            mem_data = func_data[func_data["memory_mb"] == mem].dropna(subset=["concurrency"])
            if mem_data.empty:
                continue
            mem_data = mem_data.sort_values("concurrency")
            color = colors.get(mem, "#999")
            
            ax.errorbar(
                mem_data["concurrency"],
                mem_data["avg_response_time"],
                yerr=mem_data["ci_95"],
                fmt="o-",
                color=color,
                label=f"{mem}MB (mean ± 95% CI)",
                linewidth=2,
                capsize=5,
                capthick=2,
            )
            ax.plot(
                mem_data["concurrency"],
                mem_data["p95"],
                "s--",
                color=color,
                label=f"{mem}MB (p95)",
                alpha=0.7,
            )
            ax.plot(
                mem_data["concurrency"],
                mem_data["p99"],
                "^:",
                color=color,
                label=f"{mem}MB (p99)",
                alpha=0.5,
            )
        ax.set_xlabel("Concurrency Level", fontsize=11)
        ax.set_ylabel("Response Time (ms)", fontsize=11)
        ax.set_title(f"Response vs Concurrency ({func}) — rate={rate}", fontsize=12)
        conc_vals = sorted(func_data["concurrency"].dropna().unique())
        if len(conc_vals):
            ax.set_xticks(conc_vals)
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, f"response_vs_concurrency_{rate}.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"saved {path}")


def plot_throughput_vs_concurrency(df, rate: str):
    d = _filter_steady_for_concurrency_plots(df, rate)
    if d.empty:
        print(f"skipping throughput_vs_concurrency, no steady rows for rate={rate}")
        return

    functions = sorted(d["function"].unique())
    memory_sizes = sorted(d["memory_mb"].unique())
    fig, axes = plt.subplots(1, len(functions), figsize=(7 * len(functions), 5), squeeze=False)
    colors = {128: "#2196F3", 512: "#FF9800", 1024: "#4CAF50"}

    for i, func in enumerate(functions):
        ax = axes[0][i]
        func_data = d[d["function"] == func]
        for mem in memory_sizes:
            mem_data = func_data[func_data["memory_mb"] == mem].dropna(subset=["concurrency"])
            if mem_data.empty:
                continue
            mem_data = mem_data.sort_values("concurrency")
            color = colors.get(mem, "#999")
            ax.plot(
                mem_data["concurrency"],
                mem_data["requests_per_sec"],
                "o-",
                color=color,
                label=f"{mem}MB",
                linewidth=2,
                markersize=8,
            )
        ax.set_xlabel("Concurrency Level", fontsize=11)
        ax.set_ylabel("Throughput (req/s)", fontsize=11)
        ax.set_title(f"Throughput vs Concurrency ({func}) — rate={rate}", fontsize=12)
        conc_vals = sorted(func_data["concurrency"].dropna().unique())
        if len(conc_vals):
            ax.set_xticks(conc_vals)
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, f"throughput_vs_concurrency_{rate}.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"saved {path}")


def plot_rate_sensitivity(df):
    d = df[df["load_pattern"] != "burst"].dropna(subset=["concurrency"]).copy()
    if d.empty:
        return
    rate_order = ["low", "med", "high"]
    present = set(d["rate"].dropna().unique())
    rates = [r for r in rate_order if r in present]
    if len(rates) < 2:
        print("skipping rate_sensitivity, need at least two rate profiles")
        return

    key = ["function", "memory_mb", "concurrency"]
    full_groups = [
        (k, g) for k, g in d.groupby(key)
        if set(g["rate"].unique()) >= set(rates)
    ]
    n_plots = len(full_groups)
    if n_plots == 0:
        print("skipping rate_sensitivity, no groups with complete low med high sweep")
        return

    n_cols = min(3, n_plots)
    n_rows = int(np.ceil(n_plots / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows), squeeze=False)
    axes_flat = axes.flatten()

    for ax, ((func, mem, conc), g) in zip(axes_flat, full_groups):
        g = g.sort_values("rate")
        x = np.arange(len(rates))
        by_rate = {r: g[g["rate"] == r] for r in rates}
        avgs = [float(by_rate[r]["avg_response_time"].iloc[0]) if len(by_rate[r]) else 0 for r in rates]
        cis = [float(by_rate[r]["ci_95"].iloc[0]) if len(by_rate[r]) else 0 for r in rates]
        p99s = [float(by_rate[r]["p99"].iloc[0]) if len(by_rate[r]) else 0 for r in rates]

        width = 0.35
        ax.bar(x - width/2, avgs, width, yerr=cis, color="steelblue", alpha=0.9, capsize=5, label="Avg ± 95% CI")
        ax.bar(x + width/2, p99s, width, color="tomato", alpha=0.85, label="p99")
        ax.set_xticks(x)
        ax.set_xticklabels(rates)
        ax.set_title(f"{func} {mem}MB c={int(conc)}")
        ax.set_ylabel("Response Time (ms)")
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.legend(fontsize=8)

    for j in range(n_plots, len(axes_flat)):
        axes_flat[j].set_visible(False)

    plt.suptitle("Steady Load: Avg Response Time by Request-Rate Profile (with 95% CI)", fontsize=12)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "rate_sensitivity_sample.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"saved {path}")


def plot_burst_vs_steady(df):
    burst_rows = df[df["load_pattern"] == "burst"]
    if burst_rows.empty:
        print("skipping burst_vs_steady, no burst runs")
        return

    steady_ref = df[(df["load_pattern"] == "steady") & (df["concurrency"] == 25) & (df["rate"] == "med")]

    for _, b in burst_rows.iterrows():
        func, mem = b["function"], b["memory_mb"]
        srows = steady_ref[(steady_ref["function"] == func) & (steady_ref["memory_mb"] == mem)]
        if srows.empty:
            srows = df[
                (df["load_pattern"] == "steady")
                & (df["function"] == func)
                & (df["memory_mb"] == mem)
                & (df["rate"] == "med")
            ].sort_values("concurrency", ascending=False)
            if srows.empty:
                continue
            s = srows.iloc[0]
        else:
            s = srows.iloc[0]

        steady_conc = int(s.get("concurrency", 25)) if pd.notna(s.get("concurrency")) else 25
        labels = [f"Steady (c={steady_conc}, med)", "Burst (1→50)"]
        avg_rt = [s["avg_response_time"], b["avg_response_time"]]
        p95_rt = [s["p95"], b["p95"]]
        p99_rt = [s["p99"], b["p99"]]
        ci_vals = [s.get("ci_95", 0), b.get("ci_95", 0)]

        x = np.arange(len(labels))
        width = 0.25
        fig, ax = plt.subplots(figsize=(9, 6))
        
        bars1 = ax.bar(x - width, avg_rt, width, yerr=ci_vals, label="Avg ± 95% CI", 
                       color="steelblue", capsize=5)
        bars2 = ax.bar(x, p95_rt, width, label="p95", color="orange")
        bars3 = ax.bar(x + width, p99_rt, width, label="p99", color="tomato")
        
        ax.set_title(f"Steady vs Burst — {func} ({mem}MB)", fontsize=13)
        ax.set_ylabel("Response Time (ms)", fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.legend(fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.annotate(f'{height:.0f}',
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),
                                textcoords="offset points",
                                ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        safe = f"{func}_{mem}mb".replace("/", "_")
        path = os.path.join(OUTPUT_DIR, f"burst_vs_steady_{safe}.png")
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"saved {path}")


def plot_memory_comparison(df):
    d = df[(df["load_pattern"] != "burst") & (df["rate"] == "med")].dropna(subset=["concurrency"]).copy()
    if d.empty:
        return
    
    for func in d["function"].unique():
        func_data = d[d["function"] == func]
        conc_levels = sorted(func_data["concurrency"].unique())
        mem_sizes = sorted(func_data["memory_mb"].unique())
        
        if len(mem_sizes) < 2:
            continue
        
        fig, axes = plt.subplots(1, len(conc_levels), figsize=(6 * len(conc_levels), 5), squeeze=False)
        
        for i, conc in enumerate(conc_levels):
            ax = axes[0][i]
            conc_data = func_data[func_data["concurrency"] == conc].sort_values("memory_mb")
            
            x = np.arange(len(conc_data))
            width = 0.35
            
            ax.bar(x - width/2, conc_data["avg_response_time"], width, 
                   yerr=conc_data["ci_95"], label="Avg ± 95% CI", capsize=5, color="steelblue")
            ax.bar(x + width/2, conc_data["p99"], width, label="p99", color="tomato")
            
            ax.set_xlabel("Memory Size (MB)")
            ax.set_ylabel("Response Time (ms)")
            ax.set_title(f"{func} @ c={int(conc)}")
            ax.set_xticks(x)
            ax.set_xticklabels([f"{int(m)}MB" for m in conc_data["memory_mb"]])
            ax.legend()
            ax.grid(axis="y", alpha=0.3)
        
        plt.suptitle(f"Memory Size Impact on Response Time ({func})", fontsize=12)
        plt.tight_layout()
        path = os.path.join(OUTPUT_DIR, f"memory_comparison_{func}.png")
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"saved {path}")


def print_summary_table(df):
    cols = [
        "load_pattern",
        "function",
        "memory_mb",
        "concurrency",
        "rate",
        "avg_response_time",
        "std_response_time",
        "ci_95",
        "median_response_time",
        "p95",
        "p99",
        "min_response_time",
        "max_response_time",
        "requests_per_sec",
        "failure_count",
        "total_requests",
        "source_file",
    ]
    present = [c for c in cols if c in df.columns]
    summary = df[present].sort_values(
        ["function", "memory_mb", "load_pattern", "concurrency", "rate"],
        na_position="last",
    )
    
    print("\ncomprehensive results summary with statistical analysis")
    
    display_df = summary.copy()
    numeric_cols = ["avg_response_time", "std_response_time", "ci_95", "median_response_time", 
                    "p95", "p99", "min_response_time", "max_response_time", "requests_per_sec"]
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].round(2)
    
    print(display_df.to_string(index=False))
    
    summary.to_csv(os.path.join(OUTPUT_DIR, "summary_table.csv"), index=False)
    print(f"\nsaved {os.path.join(OUTPUT_DIR, 'summary_table.csv')}")

    latex_cols = ["function", "memory_mb", "concurrency", "rate", "avg_response_time", 
                  "std_response_time", "ci_95", "p95", "p99", "total_requests"]
    latex_present = [c for c in latex_cols if c in summary.columns]
    latex_df = summary[latex_present].copy()
    for col in ["avg_response_time", "std_response_time", "ci_95", "p95", "p99"]:
        if col in latex_df.columns:
            latex_df[col] = latex_df[col].round(1)
    
    latex_path = os.path.join(OUTPUT_DIR, "summary_table_latex.txt")
    with open(latex_path, "w") as f:
        f.write("% LaTeX table for final report\n")
        f.write(latex_df.to_latex(index=False, float_format="%.1f"))
    print(f"saved {latex_path}")


def print_statistical_summary(df):
    print("\nstatistical summary by factor")
    
    print("\nby function")
    for func in sorted(df["function"].unique()):
        func_data = df[df["function"] == func]
        print(f"\n{func}")
        print(f"  avg response time: {func_data['avg_response_time'].mean():.2f} ms (overall mean)")
        print(f"  std dev range: {func_data['std_response_time'].min():.2f} to {func_data['std_response_time'].max():.2f} ms")
        print(f"  p99 range: {func_data['p99'].min():.2f} to {func_data['p99'].max():.2f} ms")
    
    print("\nby memory size")
    for mem in sorted(df["memory_mb"].unique()):
        mem_data = df[df["memory_mb"] == mem]
        print(f"\n{mem}mb")
        print(f"  avg response time: {mem_data['avg_response_time'].mean():.2f} ms")
        print(f"  p99 mean: {mem_data['p99'].mean():.2f} ms")
    
    print("\nby load pattern")
    for pattern in df["load_pattern"].unique():
        pat_data = df[df["load_pattern"] == pattern]
        print(f"\n{pattern}")
        print(f"  avg response time: {pat_data['avg_response_time'].mean():.2f} ms")
        print(f"  p99 mean: {pat_data['p99'].mean():.2f} ms")
        print(f"  total failure count: {pat_data['failure_count'].sum()}")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"loading results from {RESULTS_DIR}")
    df = load_all_results()
    
    if df.empty:
        print(f"error: no results found in {RESULTS_DIR}")
        print("run the test scripts first")
        print("  ./run_tests.sh")
        print("  ./run_burst_tests.sh")
        exit(1)
    
    print(f"loaded {len(df)} test scenarios")
    print(f"functions: {sorted(df['function'].unique())}")
    print(f"memory sizes: {sorted(df['memory_mb'].unique())}")
    print(f"load patterns: {sorted(df['load_pattern'].unique())}")
    
    for r in sorted(df[df["load_pattern"] != "burst"]["rate"].dropna().unique()):
        plot_response_vs_concurrency(df, r)
        plot_throughput_vs_concurrency(df, r)
    
    plot_rate_sensitivity(df)
    plot_burst_vs_steady(df)
    plot_memory_comparison(df)
    
    print_summary_table(df)
    print_statistical_summary(df)
    
    print("\nanalysis complete")
    print(f"graphs saved to {OUTPUT_DIR}/")
