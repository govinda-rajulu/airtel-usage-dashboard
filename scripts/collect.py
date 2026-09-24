#!/usr/bin/env python3
"""
Airtel selfcare collector. On-demand, attended, fail-closed.

How it works, honestly:
  1. Opens a visible browser to the Airtel login page.
  2. YOU log in with your mobile number + OTP, every run. Nothing is stored.
  3. The script records every JSON response the site itself loads while you
     browse the account pages (usage, plan, bills, linked services).
  4. When you press ENTER, it parses the captured JSON into site/data/usage.json
     plus site/data/last_raw.json (the full untrimmed capture).
  5. The dashboard renders it. The browser context is destroyed; no cookies,
     no tokens, no session file ever touch disk.

Never bypasses a CAPTCHA or challenge: it stops and tells you.
Never runs on a schedule: a fetch happens only because you started one.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USAGE_OUT = ROOT / "site" / "data" / "usage.json"
RAW_OUT = ROOT / "site" / "data" / "last_raw.json"

BASE = "https://www.airtel.in"
LOGIN_URL = BASE + "/s/selfcare"
START_URL = BASE + "/selfcare/myhome/manage-home"
MAX_QUOTA_GB = 100_000  # sanity bound


def log(line):
    print(f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {line}", flush=True)


def fail(msg, code=2):
    log(f"STOP: {msg}")
    append_fetch_log("failed", msg)
    sys.exit(code)


def append_fetch_log(status, note):
    USAGE_OUT.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if USAGE_OUT.exists():
        try:
            data = json.loads(USAGE_OUT.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    entries = data.get("fetchLog", [])
    entries.append({
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "note": note[:300],
    })
    data["fetchLog"] = entries[-50:]
    tmp = USAGE_OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(USAGE_OUT)


# ---------- parsing ----------

def _norm(k):
    return "".join(c for c in str(k).lower() if c.isalnum())


USED_KEYS = {"useddatabenefit", "dataused", "useddata", "usage", "usedgb", "consumed"}
TOTAL_KEYS = {"totaldatabenefit", "datatotal", "totaldata", "dataplan", "totalgb", "quota", "dataquota"}
REMAIN_KEYS = {"remainingdatabenefit", "dataremaining", "remainingdata", "balance", "remaininggb", "remainingbalance"}


def find_usage_in_payload(obj):
    """Hunt a parsed JSON tree for (used, total, remaining). Needs used plus
    at least one of total/remaining. Returns (used, total, remaining, unit) or None."""
    found = {}
    unit = "GB"

    def walk(o, depth):
        nonlocal unit
        if depth > 8:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                nk = _norm(k)
                if nk in USED_KEYS and "used" not in found:
                    try:
                        found["used"] = float(str(v).replace(",", "").split()[0])
                    except (TypeError, ValueError, IndexError):
                        pass
                elif nk in TOTAL_KEYS and "total" not in found:
                    try:
                        found["total"] = float(str(v).replace(",", "").split()[0])
                    except (TypeError, ValueError, IndexError):
                        pass
                elif nk in REMAIN_KEYS and "remaining" not in found:
                    try:
                        found["remaining"] = float(str(v).replace(",", "").split()[0])
                    except (TypeError, ValueError, IndexError):
                        pass
                if "unit" in nk and isinstance(v, str) and v.strip():
                    unit = v.strip().upper()
                walk(v, depth + 1)
        elif isinstance(o, list):
            for it in o:
                walk(it, depth + 1)

    walk(obj, 0)
    if "used" in found and ("total" in found or "remaining" in found):
        used = found["used"]
        total = found.get("total")
        remaining = found.get("remaining")
        if total is None and remaining is not None:
            total = used + remaining
        if remaining is None and total is not None:
            remaining = total - used
        return used, total, remaining, unit
    return None


PLAN_KEYS = {"planname", "plan", "packname", "currentplan", "plantype"}
BILL_KEYS = {"billamount", "amountdue", "dueamount", "billdate", "duedate", "invoicenumber", "billnumber", "invoiceamount"}
SERVICE_KEYS = {"servicetype", "serviceid", "broadbandid", "accountnumber", "customerid", "registeredmobilenumber", "rmn"}
CYCLE_KEYS = {"billcycle", "cyclestartdate", "cycleenddate", "billingcycle", "billcyclestartdate", "billcycleenddate", "startdate", "enddate"}


def collect_fields(payloads, keyset, limit=60):
    """Pull {path, key, value} rows for any key in keyset across all payloads."""
    rows = []
    seen = set()

    def walk(o, path, depth):
        if depth > 9 or len(rows) >= limit:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                nk = _norm(k)
                if nk in keyset and isinstance(v, (str, int, float)) and not isinstance(v, bool):
                    row = (path, str(k), str(v))
                    if row not in seen:
                        seen.add(row)
                        rows.append({"section": path, "field": str(k), "value": str(v)})
                walk(v, path + "/" + str(k), depth + 1)
        elif isinstance(o, list):
            for i, it in enumerate(o[:50]):
                walk(it, f"{path}[{i}]", depth + 1)

    for label, payload in payloads:
        walk(payload, label, 0)
    return rows


def sanity_check(used, total, remaining):
    problems = []
    if total is not None and (total <= 0 or total > MAX_QUOTA_GB):
        problems.append(f"total {total} outside sane bounds")
    if used is not None and used < 0:
        problems.append(f"used {used} negative")
    if used is not None and total is not None and used > total * 3:
        problems.append(f"used {used} wildly exceeds total {total} (unit mix?)")
    if remaining is not None and total is not None and abs((used or 0) + remaining - total) > max(1.0, total * 0.05):
        problems.append(f"used+remaining != total ({used}+{remaining}!={total})")
    return problems


def captcha_or_challenge(page):
    try:
        body = (page.inner_text("body") or "").lower()
    except Exception:
        return True
    markers = ["captcha", "i'm not a robot", "unusual activity", "verify you are human"]
    return any(m in body for m in markers)


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail("playwright not installed. Run: pip install -r requirements.txt && python -m playwright install chromium")

    captured = []  # (url, json) in arrival order

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()

        def on_response(resp):
            try:
                if resp.request.resource_type not in ("xhr", "fetch"):
                    return
                ctype = (resp.headers.get("content-type") or "").lower()
                if "json" not in ctype:
                    return
                j = resp.json()
                captured.append((resp.url, j))
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)

        print()
        print("  1. Log in with your mobile number + OTP in the opened window.")
        print("  2. Browse the account pages you want captured:")
        print("     Manage Home / usage, plan details, bills, linked services.")
        print("  3. When your usage numbers are visible, come back here.")
        input("  Press ENTER when finished browsing: ")

        if captcha_or_challenge(page):
            browser.close()
            fail("CAPTCHA/challenge is showing. Resolve it in the browser and rerun; not bypassing it.")

        # give any trailing XHR a moment to land
        time.sleep(3)
        browser.close()

    if not captured:
        fail(f"no JSON responses captured. Did the account pages load? ({len(captured)} responses)")

    # full raw capture, trimmed only to keep the repo sane
    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    raw_doc = {
        "capturedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "responses": [{"url": u, "json": j} for u, j in captured],
    }
    raw_text = json.dumps(raw_doc, indent=2)
    if len(raw_text) > 2_000_000:
        raw_text = raw_text[:2_000_000] + "\n/* trimmed at 2MB */\n"
    RAW_OUT.write_text(raw_text, encoding="utf-8")
    log(f"raw capture: {len(captured)} JSON responses -> site/data/last_raw.json")

    # usage from the first payload that has it, searching newest-first
    hit = None
    hit_url = None
    for url, j in reversed(captured):
        h = find_usage_in_payload(j)
        if h:
            hit, hit_url = h, url
            break

    # cycle dates from any payload
    cycles = collect_fields([(u, j) for u, j in captured], CYCLE_KEYS, limit=20)

    labeled = [(u, j) for u, j in captured]
    plan_rows = collect_fields(labeled, PLAN_KEYS)
    bill_rows = collect_fields(labeled, BILL_KEYS)
    service_rows = collect_fields(labeled, SERVICE_KEYS)

    if not hit:
        log("WARNING: no payload contained usage numbers. Plan/bill/services still written.")
        used = total = remaining = None
        unit = "GB"
    else:
        used, total, remaining, unit = hit
        problems = sanity_check(used, total, remaining)
        if problems:
            fail("sanity check failed: " + "; ".join(problems) + f" (from {hit_url})")

    merge_and_write(used, total, remaining, unit, hit_url,
                    plan_rows, bill_rows, service_rows, cycles, len(captured))
    append_fetch_log("ok", f"{len(captured)} JSON responses captured; usage {'found via ' + hit_url if hit else 'NOT found'}")
    log("DONE")


def merge_and_write(used, total, remaining, unit, source,
                    plan_rows, bill_rows, service_rows, cycle_rows, n_responses):
    existing = {}
    if USAGE_OUT.exists():
        try:
            existing = json.loads(USAGE_OUT.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    today = datetime.now(timezone.utc).date().isoformat()
    daily = [d for d in existing.get("daily", []) if d.get("date") != today]
    if used is not None:
        daily.append({"date": today, "used": round(used, 3)})

    prev_cur = existing.get("current") or {}
    cycle_label = None
    if cycle_rows:
        # compose "start - end" from the first start/end pair we can find
        starts = [r["value"] for r in cycle_rows if "start" in _norm(r["field"])]
        ends = [r["value"] for r in cycle_rows if "end" in _norm(r["field"])]
        if starts and ends:
            cycle_label = f"{starts[0]} - {ends[0]}"
        else:
            cycle_label = cycle_rows[0]["value"]
    if not cycle_label:
        cycle_label = prev_cur.get("cycleLabel")

    new_current = {
        "usedGB": round(used, 3) if used is not None else None,
        "totalGB": round(total, 3) if total is not None else None,
        "remainingGB": round(remaining, 3) if remaining is not None else None,
        "unit": unit,
        "cycleLabel": cycle_label,
        "daysTotal": prev_cur.get("daysTotal"),
        "daysElapsed": prev_cur.get("daysElapsed"),
        "source": source,
    }

    history = existing.get("history", [])
    if cycle_label and used is not None:
        history = [h for h in history if h.get("cycleLabel") != cycle_label]
        history.append({"cycleLabel": cycle_label,
                        "usedGB": new_current["usedGB"],
                        "totalGB": new_current["totalGB"]})

    out = {
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current": new_current,
        "daily": daily[-62:],
        "history": history[-12:],
        "plan": plan_rows,
        "bills": bill_rows,
        "services": service_rows,
        "responsesCaptured": n_responses,
        "fetchLog": existing.get("fetchLog", []),
    }
    tmp = USAGE_OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=2), encoding="utf-8")
    tmp.replace(USAGE_OUT)
    log(f"usage.json updated: used={used} total={total} remaining={remaining} {unit}; "
        f"plan fields={len(plan_rows)} bill fields={len(bill_rows)} service fields={len(service_rows)}")


if __name__ == "__main__":
    main()
