# OWASP ZAP session analysis

This document summarizes the Ubian web flow observed in the provided OWASP ZAP
session. Sensitive values such as email, password, cookies, session IDs and real
card numbers are intentionally omitted.

## Relevant flow

1. Open `GET https://www.ubian.sk/login`.
2. Submit `POST https://www.ubian.sk/login` with form data:
   - `email`
   - `password`
   - `rememberme=on`
3. Successful login returns `302` with `Location: /eshop?product=pcl` and a
   `PHPSESSID` cookie.
4. Load `GET https://www.ubian.sk/eshop`.
5. Parse the card selector from the HTML:
   - card id is stored in `a.js-set-active-card[data-snr]`
   - description is stored in `.title-label`
   - display card number is stored in `.card-no`
   - the active card is marked by `li.current-card`
6. Parse the active card balance from the HTML text matching `Kredit <amount> €`.
7. Parse active card details from the `.infolist` section:
   - `Platnosť karty`
   - `Typ karty`
   - `Platnosť zľavy`
8. To read another card, call `POST https://www.ubian.sk/card/set_active` with
   `snr=<card id>` and header `X-Requested-With: XMLHttpRequest`.
9. The response is JSON: `{"status":"ok"}`.
10. Reload `GET https://www.ubian.sk/eshop` and parse the newly active card.

## Implementation notes

The current integration uses the web session flow because the ZAP capture did not
show a dedicated JSON endpoint for listing cards with balances. The integration
temporarily changes the active card while polling and then attempts to restore
the card that was active before the update.
