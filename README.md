# Ubian Home Assistant integration

Custom Home Assistant integration for Ubian card credit balances.

## Current scope

- UI configuration with email, password and update interval.
- Default update interval is 5 minutes.
- One sensor entity is created for every Ubian card returned by the account.
- Each entity exposes the card id, description and credit balance as attributes.
- The current API client follows the observed Ubian web flow from OWASP ZAP:
  login, load `/eshop`, parse cards from HTML, temporarily switch active cards
  through `/card/set_active`, and parse each active card balance from `/eshop`.

## Notes

- The ZAP session files contain sensitive data such as credentials and session
  cookies. Do not commit or share them.
- A sanitized flow summary is available in `docs/zap-analysis.md`.

## HACS

Add this repository as a custom HACS repository with category `Integration`.
Use a GitHub release, for example `0.1.0`, for the most reliable install path.
