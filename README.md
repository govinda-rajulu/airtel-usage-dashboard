# Airtel Account Dashboard

Static GitHub Pages dashboard aggregating the details Airtel exposes for this account: plan, linked connections, current bill, bill history, and shortcuts. The broadband-usage slot stays empty until Airtel's portal exposes real figures again.

## Privacy rule (hard)

This repo is public. `docs/data/usage.json` is published with masked identifiers (mobile, email, account numbers). **Never push raw captures, HAR files, headers, cookies, tokens, or unmasked account data.** The importer masks before writing; verify with `git diff` anyway.

## Realtime: the live overlay

`tools-airtel-live.js` is the live version. Copy it, paste into the browser console on a logged-in airtel.in tab, navigate normally, click **Build / refresh**. It aggregates the session's own Airtel responses and probes the usage endpoint live, masking everything on screen. Nothing is stored or uploaded; closing the tab ends it. "Copy sanitized JSON" gives a masked export you can feed to the importer.

## Static publish routine

`python3 scripts/import_capture.py <capture.json>`, review the diff, stage only intended files, commit, push.
