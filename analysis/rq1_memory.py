import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent     # the analysis/ folder
FIG_DIR = HERE / "figures"
FIG_DIR.mkdir(exist_ok=True) 

def build_graph1(df):
    fig, ax = plt.subplots()
    for workload, group in df.groupby("workload"):
        ax.plot(group["memory_mb"], group["mean_ms"], marker="o", label=workload)
    ax.set_xscale("log")           
    ax.set_yscale("log")
    ax.set_yticks([ 30, 100, 300, 1000, 3000])         
    ax.set_xticks([512, 1024, 1769])
    ax.set_xticklabels([512,1024, 1769])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(25, 3500)
    
    ax.set_xlabel("Memory (MB)")
    ax.set_ylabel("Mean response time (ms, log)")
    ax.set_title("Response time vs memory")
    ax.legend(title="Workload")
    fig.savefig(FIG_DIR / "graph1_response_vs_memory.png", dpi=150, bbox_inches="tight")

def build_graph2(df):
    fig, ax = plt.subplots()
    for workload, group in df.groupby("workload"):
        ax.plot(group["memory_mb"], group["throughput_rps"], marker="o", label=workload)
    ax.set_xticks([512, 1024, 1769])
    ax.set_xlabel("Memory (MB)")
    ax.set_ylabel("Successful throughput (requests/s)")
    ax.set_title("Throughput vs memory")
    ax.legend(title="Workload")
    fig.savefig(FIG_DIR / "graph1_throughput_vs_memory.png", dpi=150, bbox_inches="tight")

def build_supporting_table(df): 
    # ---- RQ1 supporting table ----
    table = df[["setup", "exec_mean_ms", "max_memory_used_mb", "cost_per_million_usd"]]
    table.to_csv(HERE/"rq1_table.csv", index=False)
    print(df)
    print(table.round(2).to_string(index=False))


def main(): 
    df = pd.read_csv(HERE / "per_config.csv")
    print(df.columns.tolist())
    print(df[['setup', 'workload', 'memory_mb','users','mean_ms', 'median_ms', 'std_ms', 'p95_ms', 'p99_ms', 'throughput_rps', 'failure_rate', 'exec_mean_ms', 'overhead_ms', 'max_memory_used_mb', 'cost_per_million_usd', 'cold_starts', 'peak_concurrency']])
    df = df[~df["setup"].isin(["cpu-1024-low", "cpu-1024-high"])]
    
    df = df.sort_values(["workload", "memory_mb"])
    print(df)

    build_graph1(df)

    build_graph2(df)
    build_supporting_table(df)

    

if __name__ == "__main__":
    main()