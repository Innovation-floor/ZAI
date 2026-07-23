#!/usr/bin/env bash
# Smoke test against a running stack. Verifies every scripted demonstration
# question resolves, and that the dashboard reconciles to the executive deck.
set -euo pipefail
BASE="${1:-http://localhost:${API_PORT:-8010}}"
pass=0; fail=0

check() {
  local label="$1" actual="$2" expected="$3"
  if [[ "$actual" == "$expected" ]]; then
    printf '  \033[32mPASS\033[0m  %-46s %s\n' "$label" "$actual"; pass=$((pass+1))
  else
    printf '  \033[31mFAIL\033[0m  %-46s got %s, expected %s\n' "$label" "$actual" "$expected"; fail=$((fail+1))
  fi
}

q() { curl -fsS -X POST "$BASE/api/query" -H 'content-type: application/json' \
        -d "{\"question\":\"$1\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)$2)"; }

echo "ZAI smoke test -> $BASE"
echo
echo "Health"
check "readiness" "$(curl -fsS "$BASE/api/health/ready" | python3 -c 'import sys,json;print(json.load(sys.stdin)["status"])')" "ready"

echo
echo "Dashboard reconciles to the executive deck"
O=$(curl -fsS "$BASE/api/portfolio/overview")
check "total projects"  "$(echo "$O" | python3 -c 'import sys,json;print(json.load(sys.stdin)["summary"]["projects"])')" "210"
check "countries"       "$(echo "$O" | python3 -c 'import sys,json;print(json.load(sys.stdin)["summary"]["countries"])')" "24"

echo
echo "Scripted demonstration questions"
check "education projects in Jordan" "$(q 'show education projects in Jordan' '["summary"]["projects"]')" "12"
check "water projects in Africa"     "$(q 'show water projects in Africa' '["summary"]["countries"]')" "6"
check "Arabic education query"       "$(q 'أظهر مشاريع التعليم' '["language"]')" "ar"
check "compare Jordan and Egypt"     "$(q 'compare Jordan and Egypt' '["intent"]')" "compare"

echo
echo "Follow-up refinement semantics"
SID=$(curl -fsS -X POST "$BASE/api/query" -H 'content-type: application/json' \
      -d '{"question":"show projects in Jordan"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["session_id"])')
curl -fsS -X POST "$BASE/api/query" -H 'content-type: application/json' \
  -d "{\"question\":\"only education\",\"session_id\":\"$SID\"}" >/dev/null
R=$(curl -fsS -X POST "$BASE/api/query" -H 'content-type: application/json' \
    -d "{\"question\":\"what about Egypt\",\"session_id\":\"$SID\"}")
check "same dimension replaces" \
  "$(echo "$R" | python3 -c 'import sys,json;print(",".join(json.load(sys.stdin)["state"]["filters"].get("country",[])))')" "Egypt"
check "other dimension persists" \
  "$(echo "$R" | python3 -c 'import sys,json;print(",".join(json.load(sys.stdin)["state"]["filters"].get("sector",[])))')" "Education"

echo
printf 'Result: \033[32m%d passed\033[0m, ' "$pass"
if [[ $fail -gt 0 ]]; then printf '\033[31m%d failed\033[0m\n' "$fail"; exit 1; fi
printf '0 failed\n'
