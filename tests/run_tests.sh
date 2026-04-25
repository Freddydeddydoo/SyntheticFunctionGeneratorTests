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
    "decompress-1024"
    "json2yaml-1024"
    "floatoperations-1024"
)

CONCURRENCY_LEVELS=(1 10 25)
RATE_PROFILES=(low med high)
DURATION="${DURATION:-60s}"
RESULTS_DIR="./results"
SPAWN_RATE="${SPAWN_RATE:-2}"

mkdir -p "$RESULTS_DIR"

run_one() {
    local func="$1"
    local users="$2"
    local rate="$3"
    local csv_basename="$4"

    echo ""
    echo "running steady test for $func (users=$users, rate=$rate, spawn=$SPAWN_RATE)"

    export LAMBDA_FUNCTION="$func"
    export LOCUST_RATE_PROFILE="$rate"

    locust -f locustfile.py \
        --headless \
        --users "$users" \
        --spawn-rate "$SPAWN_RATE" \
        --run-time "$DURATION" \
        --csv "$RESULTS_DIR/$csv_basename" \
        --csv-full-history \
        2>&1 | tail -8 || true

    echo "saved -> ${RESULTS_DIR}/${csv_basename}_stats.csv"
    sleep "${SLEEP_BETWEEN:-5}"
}

echo "starting steady test sweep"
echo "functions: ${FUNCTIONS[*]}"
echo "concurrency levels: ${CONCURRENCY_LEVELS[*]}"
echo "rate profiles: ${RATE_PROFILES[*]}"
echo "duration per test: $DURATION"
echo "results directory: $RESULTS_DIR"

for func in "${FUNCTIONS[@]}"; do
    for users in "${CONCURRENCY_LEVELS[@]}"; do
        if [[ "${SKIP_RATE_SWEEP:-0}" == "1" ]]; then
            rate="${LOCUST_RATE_PROFILE:-med}"
            csv_basename="steady_${func}_c${users}_r${rate}"
            run_one "$func" "$users" "$rate" "$csv_basename"
        else
            for rate in "${RATE_PROFILES[@]}"; do
                csv_basename="steady_${func}_c${users}_r${rate}"
                run_one "$func" "$users" "$rate" "$csv_basename"
            done
        fi
    done
done

echo ""
echo "steady sweep finished -> $RESULTS_DIR/"
echo "next:"
echo "  1) run burst tests: ./run_burst_tests.sh"
echo "  2) generate analysis: python analyze_results.py"
