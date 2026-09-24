# Airtel Account Dashboard

Static GitHub Pages dashboard aggregating the details Airtel exposes for Govind's account: plan, linked connections, current bill, bill history, receiver details, shortcuts, and a reserved broadband-usage slot.

## Important privacy rule

The repository is public so GitHub Pages can serve the dashboard. **Do not push raw Airtel captures, HAR files, request headers, cookies, tokens, or account responses.** Only `docs/data/usage.json`, generated from reviewed values, should be published. Keep raw captures local or share them only in the private ClickUp conversation.

## Publish routine

1. On a logged-in Airtel page, run the owner-approved capture/check snippet.
2. Save the resulting JSON privately.
3. From the repo root, run `python3 scripts/import_capture.py <capture.json>`.
4. Review the reported changes and `git diff -- docs/data/usage.json` before staging.
5. Stage only `docs/data/usage.json` and/or approved source files, commit, push, and verify the Pages deployment.

## Current evidence state

The current Airtel web portal exposes plan/bill/account details and defines a broadband usage widget, but the AirFiber page did not return consumed/remaining GB during 24 September captures. The dashboard therefore displays those available details and reserves the usage slot for real old-portal figures when they reappear.
