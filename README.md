# Ubian for Home Assistant

[Slovensky](#slovensky) | [English](#english)

Custom Home Assistant integration for Ubian cards. The integration signs in to a
Ubian account, discovers cards, reads credit balance and card metadata, and
tracks newly observed transactions as Home Assistant events.

## Slovensky

### Prehľad

Ubian pre Home Assistant je vlastná integrácia, ktorá načíta dopravné karty z
účtu Ubian a sprístupní ich ako entity v Home Assistante.

Integrácia aktuálne podporuje:

- prihlásenie cez email a heslo,
- nastaviteľný interval aktualizácie, predvolene 5 minút,
- automatické nájdenie kariet v účte,
- výšku kreditu pre každú kartu,
- platnosť karty,
- typ karty,
- platnosť zľavy,
- základné atribúty karty, napríklad číslo karty, dopravca a dátum stavu kreditu,
- posledné transakcie ako atribúty,
- event entitu `Transakcia`, ktorá sa aktivuje pri novo zistenej poslednej transakcii.

### Inštalácia cez HACS

1. V HACS otvor `Custom repositories`.
2. Pridaj repozitár:

   `https://github.com/senux1988/Ubian`

3. Ako kategóriu vyber `Integration`.
4. Nainštaluj integráciu Ubian.
5. Reštartuj Home Assistant.
6. V Home Assistante otvor `Nastavenia` -> `Zariadenia a služby` -> `Pridať integráciu`.
7. Vyhľadaj `Ubian` a zadaj prihlasovacie údaje.

### Entity

Pre každú kartu sa vytvoria senzory:

- `Výška kreditu`,
- `Platnosť karty`,
- `Typ karty`,
- `Platnosť zľavy`.

Pre každú kartu sa vytvorí aj event entita:

- `Transakcia`.

Event entita sa použije na zaznamenanie novej poslednej transakcie do aktivity
Home Assistanta. Pri prvom načítaní sa existujúca posledná transakcia uloží ako
východiskový stav, aby sa staré transakcie nehlásili ako nové.

### Poznámky

- Integrácia používa webový tok Ubianu pozorovaný cez OWASP ZAP: prihlásenie,
  načítanie `/eshop`, parsovanie HTML, dočasné prepínanie aktívnej karty cez
  `/card/set_active` a načítanie histórie cez `/transactions/<id>`.
- Ubian neposkytol oficiálne verejné API pre túto integráciu, preto sa parsuje
  webové HTML. Zmena stránky Ubianu môže vyžadovať úpravu integrácie.
- ZAP session súbory môžu obsahovať citlivé údaje, napríklad heslá, cookies a
  session tokeny. Nikdy ich necommituj ani nezdieľaj.
- Sanitizovaný technický popis toku je v `docs/zap-analysis.md`.

## English

### Overview

Ubian for Home Assistant is a custom integration that loads public transport
cards from an Ubian account and exposes them as Home Assistant entities.

The integration currently supports:

- login with email and password,
- configurable update interval, defaulting to 5 minutes,
- automatic card discovery,
- credit balance for each card,
- card validity,
- card type,
- discount validity,
- card attributes such as display card number, carrier and credit status date,
- latest transactions as attributes,
- a `Transaction` event entity that fires when a newly observed latest
  transaction appears.

### HACS Installation

1. Open `Custom repositories` in HACS.
2. Add this repository:

   `https://github.com/senux1988/Ubian`

3. Select `Integration` as the category.
4. Install the Ubian integration.
5. Restart Home Assistant.
6. In Home Assistant, go to `Settings` -> `Devices & services` -> `Add integration`.
7. Search for `Ubian` and enter your credentials.

### Entities

For every card, the integration creates sensor entities:

- `Credit balance`,
- `Card validity`,
- `Card type`,
- `Discount validity`.

For every card, the integration also creates an event entity:

- `Transaction`.

The event entity is used to record newly observed latest transactions in Home
Assistant activity/logbook. On the first update, the existing latest transaction
is stored as a baseline so old transactions are not reported as new.

### Notes

- The integration follows the Ubian web flow observed through OWASP ZAP: login,
  load `/eshop`, parse HTML, temporarily switch active cards through
  `/card/set_active`, and load transaction history through `/transactions/<id>`.
- Ubian has not provided an official public API for this integration, so the
  integration parses the website HTML. Website changes may require integration
  updates.
- ZAP session files may contain sensitive data such as passwords, cookies and
  session tokens. Never commit or share them.
- A sanitized technical flow summary is available in `docs/zap-analysis.md`.
