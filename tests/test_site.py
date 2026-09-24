#!/usr/bin/env python3
"""Site gates: assets exist, no external API calls from the page, data schema."""
import json
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
fails = []


def check(name, cond):
    if cond:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}")
        fails.append(name)


index = (SITE / "index.html").read_text(encoding="utf-8")
app = (SITE / "app.js").read_text(encoding="utf-8")
css = (SITE / "style.css").read_text(encoding="utf-8")

check("index.html nonempty", len(index) > 1000)
check("style.css nonempty", len(css) > 1000)
check("app.js nonempty", len(app) > 1000)

# The page must only ever fetch its own data file, never Airtel or any API.
fetch_calls = re.findall(r'fetch\(([^)]+)\)', app)
check("exactly one fetch() in app.js", len(fetch_calls) == 1)
check("only fetch target is data/usage.json", fetch_calls and "data/usage.json" in fetch_calls[0])
check("no airtel URL in frontend", "airtel" not in (index + app + css).lower())
check("no tracking/exfil endpoints", not re.search(r'https?://(?!fonts\.googleapis)', index + app))

# Sample data validates against what the frontend reads
sample = json.loads((SITE / "data" / "usage.json").read_text(encoding="utf-8"))
cur = sample["current"]
check("sample has current numbers", isinstance(cur["usedGB"], (int, float)) and isinstance(cur["totalGB"], (int, float)))
check("sample has daily list", isinstance(sample["daily"], list) and sample["daily"])
check("sample has history", isinstance(sample["history"], list) and sample["history"])
check("sample has fetchLog", isinstance(sample["fetchLog"], list))
check("sample has plan rows", isinstance(sample.get("plan"), list) and sample["plan"])
check("sample has bill rows", isinstance(sample.get("bills"), list) and sample["bills"])
check("sample has service rows", isinstance(sample.get("services"), list) and sample["services"])
check("raw capture file exists", (SITE / "data" / "last_raw.json").exists())
check("page links raw capture", "data/last_raw.json" in index)
check("page has plan/bills/services panels",
      all(x in index for x in ("planTable", "billTable", "serviceTable")))
for d in sample["daily"]:
    check(f"daily entry {d.get('date')} well formed", re.match(r"\d{4}-\d{2}-\d{2}$", d["date"]) and d["used"] >= 0)

print()
if fails:
    print(f"{len(fails)} FAILED")
    sys.exit(1)
print("all site gates green")
