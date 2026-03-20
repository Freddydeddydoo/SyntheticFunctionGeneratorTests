import matplotlib.pyplot as plt
import numpy as np

# Data from terminal output
# c1: 1 user, 30s run - 13 requests
c1_avg = 614
c1_p95 = 4400
c1_p99 = 4400

# c50: 50 users, 60s run - 115 requests  
c50_avg = 18278
c50_p95 = 41000
c50_p99 = 59000

# Steady: 1 user, 120s run
steady_avg = 0
steady_p95 = 0
steady_p99 = 0

# Burst: 50 users, 30s run
burst_avg = 0
burst_p95 = 0
burst_p99 = 0

# Read steady and burst from CSV
import csv

def read_aggregated(filename):
    with open(filename, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Name'] == 'Aggregated' and row['Request Count'] != '0':
                return row
    return None

steady_row = read_aggregated('results_steady_stats.csv')
burst_row = read_aggregated('results_burst_stats.csv')

if steady_row:
    steady_avg = float(steady_row['Average Response Time'])
    steady_p95 = float(steady_row['95%']) if steady_row['95%'] != 'N/A' else 0
    steady_p99 = float(steady_row['99%']) if steady_row['99%'] != 'N/A' else 0

if burst_row:
    burst_avg = float(burst_row['Average Response Time'])
    burst_p95 = float(burst_row['95%']) if burst_row['95%'] != 'N/A' else 0
    burst_p99 = float(burst_row['99%']) if burst_row['99%'] != 'N/A' else 0

# Objective 1 - Concurrency vs Response Time
labels = ['1 User (Low Load)', '50 Users (High Load)']
avg_rt = [c1_avg, c50_avg]
p95_rt = [c1_p95, c50_p95]
p99_rt = [c1_p99, c50_p99]

x = np.arange(len(labels))
width = 0.25

fig, ax = plt.subplots(figsize=(9, 6))
ax.bar(x - width, avg_rt, width, label='Avg', color='steelblue')
ax.bar(x, p95_rt, width, label='p95', color='orange')
ax.bar(x + width, p99_rt, width, label='p99', color='tomato')
ax.set_title('Objective 1: Response Time vs Concurrency\n(floatoperations-512, 512MB memory)')
ax.set_ylabel('Response Time (ms)')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
ax.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig('obj1_concurrency.png', dpi=150)
plt.close()
print("Saved obj1_concurrency.png")

# Objective 2 - Steady vs Burst
labels2 = ['Steady (1 user, 120s)', 'Burst (50 users, 30s)']
avg_rt2 = [steady_avg, burst_avg]
p95_rt2 = [steady_p95, burst_p95]
p99_rt2 = [steady_p99, burst_p99]

x2 = np.arange(len(labels2))

fig, ax = plt.subplots(figsize=(9, 6))
ax.bar(x2 - width, avg_rt2, width, label='Avg', color='steelblue')
ax.bar(x2, p95_rt2, width, label='p95', color='orange')
ax.bar(x2 + width, p99_rt2, width, label='p99', color='tomato')
ax.set_title('Objective 2: Steady vs Burst Invocation Pattern\n(floatoperations-512, 512MB memory)')
ax.set_ylabel('Response Time (ms)')
ax.set_xticks(x2)
ax.set_xticklabels(labels2)
ax.legend()
ax.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig('obj2_burst_vs_steady.png', dpi=150)
plt.close()
print("Saved obj2_burst_vs_steady.png")

print("Done")