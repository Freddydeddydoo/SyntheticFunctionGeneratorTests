#!/bin/bash

FUNCTIONS=(
    "decompress-128"
    "decompress-512"
    "decompress-1024"
    "dynamowrite-readfile-128"
    "dynamowrite-readfile-512"
    "dynamowrite-readfile-1024"
)

CONCURRENCY_LEVELS=(1 10 50)
DURATION="60s"
RESULTS_DIR="./results"

mkdir -p "$RESULTS_DIR"

for func in "${FUNCTIONS[@]}"; do
    for users in "${CONCURRENCY_LEVELS[@]}"; do
        echo ""
        echo "============================================"
        echo "Testing: $func | Concurrency: $users users"
        echo "============================================"

        export LAMBDA_FUNCTION="$func"

        locust -f locustfile.py \
            --headless \
            --users "$users" \
            --spawn-rate "$users" \
            --run-time "$DURATION" \
            --csv "$RESULTS_DIR/${func}_c${users}" \
            --csv-full-history \
            2>&1 | tail -5

        echo "Done. Results saved to $RESULTS_DIR/${func}_c${users}_stats.csv"
        echo ""

        sleep 5
    done
done

echo ""
echo "All tests complete! Results in $RESULTS_DIR/"
echo "Run 'python analyze_results.py' to generate graphs."
