#!/usr/bin/env python3
import os
import subprocess
import re

RESULTS_DIR = "./results"

REQUIRED_FUNCTIONS = [
    "floatoperations",
    "decompress",
    "json2yaml",
]

REQUIRED_MEMORY_SIZES = [128, 512]
REQUIRED_CONCURRENCY = [1, 10, 50]
REQUIRED_RATES = ["low", "med", "high"]

def get_deployed_functions():
    try:
        result = subprocess.run(
            ["aws", "lambda", "list-functions", "--region", "us-west-2", 
             "--query", "Functions[].FunctionName", "--output", "text"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip().split()
        return []
    except Exception as e:
        print(f"warning: could not query aws: {e}")
        return []

def parse_result_filename(filename):
    stem = filename.replace("_stats.csv", "")

    steady_match = re.match(r"steady_(.+)-(\d+)_c(\d+)_r(low|med|high)", stem)
    if steady_match:
        return {
            "type": "steady",
            "function": steady_match.group(1),
            "memory": int(steady_match.group(2)),
            "concurrency": int(steady_match.group(3)),
            "rate": steady_match.group(4),
        }
    
    burst_match = re.match(r"burst_(.+)-(\d+)", stem)
    if burst_match:
        return {
            "type": "burst",
            "function": burst_match.group(1),
            "memory": int(burst_match.group(2)),
        }
    
    return None

def main():
    print("test progress check")
    
    print("\n1) deployed lambda functions")
    deployed = get_deployed_functions()
    if deployed:
        for func in sorted(deployed):
            print(f"  ok  {func}")
    else:
        print("  could not query aws, check credentials")
    
    print("\n2) required functions from the plan")
    needed_functions = []
    for func_base in REQUIRED_FUNCTIONS:
        for mem in REQUIRED_MEMORY_SIZES:
            func_name = f"{func_base}-{mem}"
            is_deployed = func_name in deployed
            status = "ok" if is_deployed else "missing"
            print(f"  {status} {func_name}")
            if not is_deployed:
                needed_functions.append(func_name)
    
    print("\n3) completed test results")
    
    if not os.path.exists(RESULTS_DIR):
        print("  no results directory found")
        completed_steady = []
        completed_burst = []
    else:
        files = [f for f in os.listdir(RESULTS_DIR) if f.endswith("_stats.csv")]
        completed_steady = []
        completed_burst = []
        
        for f in files:
            meta = parse_result_filename(f)
            if meta:
                if meta["type"] == "steady":
                    key = f"{meta['function']}-{meta['memory']}_c{meta['concurrency']}_r{meta['rate']}"
                    completed_steady.append(key)
                    print(f"  ok  {key}")
                else:
                    key = f"{meta['function']}-{meta['memory']}"
                    completed_burst.append(key)
                    print(f"  ok  burst_{key}")
    
    print("\n4) missing steady-state tests")
    missing_steady = []
    for func_base in REQUIRED_FUNCTIONS:
        for mem in REQUIRED_MEMORY_SIZES:
            for conc in REQUIRED_CONCURRENCY:
                for rate in REQUIRED_RATES:
                    key = f"{func_base}-{mem}_c{conc}_r{rate}"
                    if key not in completed_steady:
                        missing_steady.append(key)
                        print(f"  missing {key}")
    
    if not missing_steady:
        print("  all steady-state tests are done")
    
    print("\n5) missing burst tests")
    missing_burst = []
    for func_base in REQUIRED_FUNCTIONS:
        for mem in REQUIRED_MEMORY_SIZES:
            key = f"{func_base}-{mem}"
            if key not in completed_burst:
                missing_burst.append(key)
                print(f"  missing burst_{key}")
    
    if not missing_burst:
        print("  all burst tests are done")
    
    print("\nsummary")
    
    total_steady_required = len(REQUIRED_FUNCTIONS) * len(REQUIRED_MEMORY_SIZES) * len(REQUIRED_CONCURRENCY) * len(REQUIRED_RATES)
    total_burst_required = len(REQUIRED_FUNCTIONS) * len(REQUIRED_MEMORY_SIZES)
    
    steady_done = len(completed_steady)
    burst_done = len(completed_burst)
    
    print(f"\nsteady-state tests: {steady_done}/{total_steady_required} completed")
    print(f"burst tests: {burst_done}/{total_burst_required} completed")
    print(f"functions to deploy: {len(needed_functions)}")
    
    if needed_functions:
        print("\naction needed: deploy these functions first")
        for f in needed_functions:
            print(f"  - {f}")
    
    if missing_steady:
        print(f"\naction needed: run {len(missing_steady)} more steady-state tests")
        print("  command: ./run_tests.sh")
    
    if missing_burst:
        print(f"\naction needed: run {len(missing_burst)} more burst tests")
        print("  command: ./run_burst_tests.sh")
    
    if not needed_functions and not missing_steady and not missing_burst:
        print("\nall tests are complete, run analysis with:")
        print("  python analyze_results.py")
    
    print()

if __name__ == "__main__":
    main()
