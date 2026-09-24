# My Broadband Meter (owner guide)

A personal page that shows everything about your Airtel connection in one
place: data usage, plan, bills, linked services, plus the full raw capture
from each session. You log in with OTP **each time you run it** (a minute of
your time), and in exchange: no stored credentials anywhere, no scheduler
touching your account, nothing for Airtel to flag. That is the safest
possible design.

---

## What you need

1. A GitHub account (you have one).
2. Python 3 on your own computer (Windows/macOS/Linux all fine).

## Step 1 - Unzip and install (your computer)

Unzip `airtel-usage-dashboard.zip`, open a terminal inside the folder, run:

```bash
pip install -r requirements.txt && python -m playwright install chromium
```

One time only.

## Step 2 - Capture a session (every time you want fresh data)

```bash
python scripts/collect.py
```

A real browser opens to the Airtel login page. Log in with mobile + OTP,
then browse the pages you want captured: Manage Home (usage), plan details,
bills, linked services. When your numbers are on screen, press ENTER in the
terminal.

The script saves:
- `site/data/usage.json` (parsed usage + plan + bills + services)
- `site/data/last_raw.json` (every JSON response, unfiltered)

Then it closes the browser and throws the session away. Nothing is stored.

If a CAPTCHA appears, the script stops. Solve it in the browser and rerun.
It will never try to get past one for you.

## Step 3 - See your dashboard

Open `site/index.html` in any browser. Done. Dial, daily burn chart, month
history, plan, bills, services, raw capture link, fetch log.

To view it from your phone too: put the folder on any static host you like
(it is plain HTML, no build), or keep it local. No hosting decision is
forced on you.

## Step 4 (optional) - Put it in a private GitHub repo

```bash
cd airtel-usage-dashboard
git init -b main
git add -A
git -c user.name="Govindarajulu K" \
    -c user.email="285203866+govinda-rajulu@users.noreply.github.com" \
    commit -m "usage dashboard"
gh repo create airtel-usage-dashboard --private --source=. --push
```

Then after each capture: `git add site/data && git commit -m update && git push`.
Your history accumulates in git, private to you. (Do this from Cloud Shell
if you prefer; upload the ZIP there first via the Cloud Shell menu.)

## What was verified before shipping

37 automated gates, all green, run twice (in-place and from the shipped ZIP):
usage parser (nested keys, comma numbers, junk refusal, incomplete refusal),
sanity bounds (negative, unit-mix, inconsistency), merge behavior (daily
replace, history update, cycle-label derivation, fallback preservation),
section extractors (plan/bills/services), site schema, page-links-raw-file,
frontend-calls-nothing-external, Python compiles clean.

## The one thing I could not verify

Which JSON key names Airtel actually uses. The parser knows ~25 common
variants and records everything raw, so the dashboard fills in on your first
real run. If the usage dial shows dashes after your first login, send me
`last_raw.json` and I pin the exact keys. Plan/bills/services render from
generic field matching and usually work immediately.

## Honest limits

- One login per update. No way around OTP that is both safe and reliable.
- History accumulates only when you run it. Skip a month, that month is blank.
- If Airtel changes their site, parsing may come back empty. The raw capture
  still has your data, and the last good dashboard stays up. Nothing breaks.
