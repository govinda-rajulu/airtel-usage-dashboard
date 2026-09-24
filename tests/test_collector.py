#!/usr/bin/env python3
"""Gate tests for the collector: parser, sanity bounds, merge behavior."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import collect  # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}")
        fails.append(name)


# 1. parser finds realistic nested payload
payload = {"data": {"accounts": [{"broadband": {
    "usage": {"usedData": "182.4", "totalData": "1024", "remainingData": "841.6", "unit": "GB"}}}]}}
hit = collect.find_usage_in_payload(payload)
check("parser finds nested usage", hit is not None)
if hit:
    used, total, remaining, unit = hit
    check("parser values exact", abs(used - 182.4) < 1e-9 and total == 1024.0 and abs(remaining - 841.6) < 1e-9)
    check("parser unit", unit == "GB")

# 2. parser refuses junk (no used field)
check("parser refuses junk", collect.find_usage_in_payload({"hello": "world"}) is None)

# 3. parser refuses used-only (needs total or remaining to cross-check)
check("parser refuses incomplete", collect.find_usage_in_payload({"usedData": "5"}) is None)

# 4. comma-formatted numbers
hit2 = collect.find_usage_in_payload({"usedData": "1,234.5", "totalData": "2048"})
check("parser handles commas", hit2 is not None and abs(hit2[0] - 1234.5) < 1e-9)

# 5. sanity: negative used rejected
check("sanity rejects negative used", collect.sanity_check(-1, 100, 101))

# 6. sanity: used wildly exceeding total rejected (unit mix guard)
check("sanity rejects unit mix", collect.sanity_check(5000, 100, -4900))

# 7. sanity: used+remaining mismatch rejected
check("sanity rejects inconsistency", collect.sanity_check(50, 100, 10))

# 8. sanity: normal values accepted
check("sanity accepts normal", collect.sanity_check(182.4, 1024, 841.6) == [])

# 9. merge: daily entry for today replaced, not duplicated
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "usage.json"
    old = collect.USAGE_OUT
    collect.USAGE_OUT = out
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date().isoformat()
    out.write_text(json.dumps({
        "fetchedAt": "x", "current": {"cycleLabel": "Sep 1-30", "daysTotal": 30, "daysElapsed": 24},
        "daily": [{"date": today, "used": 100.0}, {"date": "2026-09-23", "used": 95.0}],
        "history": [{"cycleLabel": "Sep 1-30", "usedGB": 90.0, "totalGB": 1024}],
        "fetchLog": [{"at": "x", "status": "ok", "note": "seed"}],
    }))
    collect.merge_and_write(200.0, 1024.0, 824.0, "GB", "test-endpoint",
                        [{"section": "acct", "field": "planName", "value": "Fiber"}],
                        [{"section": "bills", "field": "billAmount", "value": "1297"}],
                        [],
                        [{"section": "x", "field": "cycleStartDate", "value": "2026-09-01"},
                         {"section": "x", "field": "cycleEndDate", "value": "2026-09-30"}],
                        7)
    merged = json.loads(out.read_text())
    todays = [d for d in merged["daily"] if d["date"] == today]
    check("merge replaces today's daily entry", len(todays) == 1 and todays[0]["used"] == 200.0)
    check("merge keeps yesterday", any(d["date"] == "2026-09-23" for d in merged["daily"]))
    # cycle dates present: derived label wins, old "Sep 1-30" entry is archived, not updated
    check("merge archives old cycle entry",
          any(h["cycleLabel"] == "Sep 1-30" and h["usedGB"] == 90.0 for h in merged["history"]))
    check("merge adds derived cycle entry",
          any(h["cycleLabel"] == "2026-09-01 - 2026-09-30" and h["usedGB"] == 200.0 for h in merged["history"]))
    check("merge keeps fetchLog", merged["fetchLog"] and merged["fetchLog"][0]["note"] == "seed")
    check("merge writes plan rows", merged["plan"] and merged["plan"][0]["field"] == "planName")
    check("merge writes bill rows", merged["bills"] and merged["bills"][0]["value"] == "1297")
    check("merge derives cycle label from dates", merged["current"]["cycleLabel"] == "2026-09-01 - 2026-09-30")
    check("merge stores response count", merged["responsesCaptured"] == 7)
    # fallback: second merge with no cycle rows keeps the existing label
    collect.merge_and_write(210.0, 1024.0, 814.0, "GB", "test-endpoint", [], [], [], [], 3)
    merged2 = json.loads(out.read_text())
    check("merge preserves label when no cycle rows", merged2["current"]["cycleLabel"] == "2026-09-01 - 2026-09-30")
    check("second merge updates same cycle entry",
          sum(1 for h in merged2["history"] if h["cycleLabel"] == "2026-09-01 - 2026-09-30") == 1
          and any(h["usedGB"] == 210.0 for h in merged2["history"]))
    collect.USAGE_OUT = old

# 10. section extractor pulls plan fields with their path
rows = collect.collect_fields([("acct", {"data": {"planName": "Fiber 100 Mbps", "nested": {"billAmount": 1297}}})],
                              collect.PLAN_KEYS)
check("section extractor finds planName", any(r["field"] == "planName" and r["value"] == "Fiber 100 Mbps" for r in rows))
rows2 = collect.collect_fields([("acct", {"data": {"planName": "X", "nested": {"billAmount": 1297}}})],
                               collect.BILL_KEYS)
check("section extractor finds nested billAmount", any(r["field"] == "billAmount" and r["value"] == "1297" for r in rows2))
check("section extractor ignores unmatched keys", not collect.collect_fields([("a", {"foo": "bar"})], collect.PLAN_KEYS))

print()
if fails:
    print(f"{len(fails)} FAILED: {', '.join(fails)}")
    sys.exit(1)
print("all gates green")
