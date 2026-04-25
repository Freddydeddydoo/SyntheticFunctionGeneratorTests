#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"

RESULTS_DIR="./results"
SPAWN_RATE="${SPAWN_RATE:-2}"

run_one() {
    local func="$1"
    local users="$2"
    local rate="$3"
    local duration="$4"
    local csv_basename="$5"
    local shape_arg="${6:-}"

    echo ""
    echo "running $csv_basename for $func (users=$users, rate=$rate, duration=$duration)"

    export LAMBDA_FUNCTION="$func"
    export LOCUST_RATE_PROFILE="$rate"

    if [[ -n "$shape_arg" ]]; then
        locust -f "$shape_arg" \
            --headless \
            --run-time "$duration" \
            --csv "$RESULTS_DIR/$csv_basename" \
            --csv-full-history \
            2>&1 | tail -6 || true
    else
        locust -f locustfile.py \
            --headless \
            --users "$users" \
            --spawn-rate "$SPAWN_RATE" \
            --run-time "$duration" \
            --csv "$RESULTS_DIR/$csv_basename" \
            --csv-full-history \
            2>&1 | tail -6 || true
    fi

    sleep "${SLEEP_BETWEEN:-5}"
}

FUNCTIONS=(
    "decompress-1024"
    "json2yaml-1024"
    "floatoperations-1024"
)

echo "starting 1024mb suite"

for func in "${FUNCTIONS[@]}"; do
    run_one "$func" 1 "med" "120s" "steady_${func}_c1_rmed"
    run_one "$func" 10 "med" "60s" "steady_${func}_c10_rmed"
    run_one "$func" 25 "med" "60s" "steady_${func}_c25_rmed"
done

for func in "${FUNCTIONS[@]}"; do
    run_one "$func" 10 "low" "60s" "steady_${func}_c10_rlow"
    run_one "$func" 10 "high" "60s" "steady_${func}_c10_rhigh"
done

for func in "${FUNCTIONS[@]}"; do
    export LAMBDA_FUNCTION="$func"
    export LOCUST_RATE_PROFILE="med"
    run_one "$func" "-" "med" "60s" "burst_${func}" "burst_shape.py"
done

echo ""
echo "1024mb suite finished"
