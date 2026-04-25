#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"

FUNCTIONS=(
    "decompress-128"
    "json2yaml-128"
    "floatoperations-128"
    "decompress-512"
    "json2yaml-512"
    "floatoperations-512"
)

RESULTS_DIR="./results"
DURATION="${BURST_DURATION:-55s}"
export LOCUST_RATE_PROFILE="${LOCUST_RATE_PROFILE:-med}"

mkdir -p "$RESULTS_DIR"

echo "starting burst tests"
echo "functions: ${FUNCTIONS[*]}"
echo "burst shape: 15s at 1 user, then 30s at 50 users"
echo "duration: $DURATION"

for func in "${FUNCTIONS[@]}"; do
    echo ""
    echo "running burst test for $func"
    export LAMBDA_FUNCTION="$func"

    locust -f burst_shape.py \
        --headless \
        --run-time "$DURATION" \
        --csv "$RESULTS_DIR/burst_${func}" \
        --csv-full-history \
        2>&1 | tail -15 || true
    
    echo "saved -> ${RESULTS_DIR}/burst_${func}_stats.csv"
    sleep "${SLEEP_BETWEEN:-10}"
done

echo ""
echo "burst tests finished -> $RESULTS_DIR/"
echo "next: python analyze_results.py"
