"""API client for Ubian."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from html import unescape
from html.parser import HTMLParser
import logging
import re
from typing import Any
from urllib.parse import urljoin

import aiohttp

BASE_URL = "https://www.ubian.sk"
LOGIN_PATH = "/login"
ESHOP_PATH = "/eshop"
SET_ACTIVE_CARD_PATH = "/card/set_active"

CREDIT_PATTERN = re.compile(r"Kredit\s+([0-9\s]+(?:[,.][0-9]+)?)\s*€")
COMPANY_PATTERN = re.compile(
    r'<span class="company-name[^"]*">\s*(.*?)\s*</span>', re.DOTALL
)
STATUS_DATE_PATTERN = re.compile(r"Stav k\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})")

_LOGGER = logging.getLogger(__name__)


class UbianApiError(Exception):
    """Base exception for Ubian API errors."""


class UbianAuthError(UbianApiError):
    """Raised when Ubian authentication fails."""


@dataclass(slots=True, frozen=True)
class UbianCard:
    """Ubian card data returned by the account."""

    card_id: str
    description: str
    credit_balance: Decimal
    raw: dict[str, Any]


@dataclass(slots=True, frozen=True)
class _ParsedCard:
    """Card metadata parsed from Ubian HTML."""

    snr: str
    description: str
    card_number: str
    active: bool


@dataclass(slots=True, frozen=True)
class _ParsedEshopPage:
    """Relevant account data parsed from the e-shop page."""

    cards: list[_ParsedCard]
    active_card_id: str | None
    credit_balance: Decimal
    company_name: str | None
    credit_status_date: str | None


class _UbianCardListParser(HTMLParser):
    """Parse Ubian card selector entries from the e-shop HTML."""

    def __init__(self) -> None:
        """Initialize the parser."""
        super().__init__(convert_charrefs=True)
        self.cards: list[_ParsedCard] = []
        self._li_current = False
        self._card: dict[str, Any] | None = None
        self._span_class: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle an opening HTML tag."""
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())

        if tag == "li":
            self._li_current = "current-card" in classes
            return

        if tag == "a" and "js-set-active-card" in classes:
            snr = attr_map.get("data-snr")
            if snr:
                self._card = {
                    "snr": snr,
                    "description": "",
                    "card_number": "",
                    "active": self._li_current,
                }
            return

        if tag == "span" and self._card is not None:
            self._span_class = attr_map.get("class") or ""

    def handle_endtag(self, tag: str) -> None:
        """Handle a closing HTML tag."""
        if tag == "span":
            self._span_class = None
            return

        if tag == "a" and self._card is not None:
            description = self._card["description"].strip(" \xa0-")
            card_number = self._card["card_number"].strip()
            self.cards.append(
                _ParsedCard(
                    snr=self._card["snr"],
                    description=description or card_number or self._card["snr"],
                    card_number=card_number,
                    active=self._card["active"],
                )
            )
            self._card = None
            return

        if tag == "li":
            self._li_current = False

    def handle_data(self, data: str) -> None:
        """Handle text inside relevant card selector spans."""
        if self._card is None or self._span_class is None:
            return

        text = data.strip()
        if not text:
            return

        classes = set(self._span_class.split())
        if "title-label" in classes:
            self._card["description"] += text
        elif "card-no" in classes:
            self._card["card_number"] += text


class UbianApiClient:
    """Small async client for Ubian account data."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        """Initialize the API client."""
        self._session = session
        self._email = email
        self._password = password
        self._authenticated = False

    async def async_get_cards(self) -> list[UbianCard]:
        """Return cards for the configured Ubian account."""
        await self._async_login()

        first_page = await self._async_fetch_eshop_page()
        if not first_page.cards:
            raise UbianApiError("No Ubian cards were found on the account page.")

        original_active_card_id = first_page.active_card_id
        cards: list[UbianCard] = []

        try:
            for card in first_page.cards:
                page = first_page
                if card.snr != first_page.active_card_id:
                    await self._async_set_active_card(card.snr)
                    page = await self._async_fetch_eshop_page()

                cards.append(
                    UbianCard(
                        card_id=card.snr,
                        description=card.description,
                        credit_balance=page.credit_balance,
                        raw={
                            "card_number": card.card_number,
                            "company_name": page.company_name,
                            "credit_status_date": page.credit_status_date,
                            "active": card.snr == original_active_card_id,
                        },
                    )
                )
        finally:
            if original_active_card_id is not None:
                try:
                    await self._async_set_active_card(original_active_card_id)
                except UbianApiError:
                    _LOGGER.debug("Unable to restore the previously active Ubian card.")

        return cards

    async def _async_login(self) -> None:
        """Authenticate using the Ubian web login form."""
        if self._authenticated:
            return

        async with self._session.get(urljoin(BASE_URL, LOGIN_PATH)) as response:
            if response.status >= 400:
                raise UbianAuthError("Unable to open the Ubian login page.")
            await response.text()

        async with self._session.post(
            urljoin(BASE_URL, LOGIN_PATH),
            data={
                "email": self._email,
                "password": self._password,
                "rememberme": "on",
            },
            allow_redirects=False,
            headers={
                "Origin": BASE_URL,
                "Referer": urljoin(BASE_URL, LOGIN_PATH),
            },
        ) as response:
            if response.status not in (301, 302, 303):
                raise UbianAuthError("Ubian login failed.")

            location = response.headers.get("Location", "")
            if not location.startswith(ESHOP_PATH):
                raise UbianAuthError("Ubian login did not return the account page.")

        self._authenticated = True

    async def _async_fetch_eshop_page(self) -> _ParsedEshopPage:
        """Fetch and parse the Ubian e-shop page."""
        async with self._session.get(urljoin(BASE_URL, ESHOP_PATH)) as response:
            if response.status in (301, 302, 303):
                self._authenticated = False
                raise UbianAuthError("Ubian session expired.")

            if response.status >= 400:
                raise UbianApiError("Unable to fetch Ubian cards.")

            return _parse_eshop_page(await response.text())

    async def _async_set_active_card(self, card_id: str) -> None:
        """Set the selected card as active in the Ubian session."""
        async with self._session.post(
            urljoin(BASE_URL, SET_ACTIVE_CARD_PATH),
            data={"snr": card_id},
            headers={
                "Origin": BASE_URL,
                "Referer": urljoin(BASE_URL, ESHOP_PATH),
                "X-Requested-With": "XMLHttpRequest",
            },
        ) as response:
            if response.status >= 400:
                raise UbianApiError("Unable to select an Ubian card.")

            payload = await response.json(content_type=None)
            if payload.get("status") != "ok":
                raise UbianApiError("Ubian did not confirm card selection.")


def _parse_eshop_page(html: str) -> _ParsedEshopPage:
    """Parse cards and the active card credit balance from Ubian HTML."""
    parser = _UbianCardListParser()
    parser.feed(html)

    active_card_id = next((card.snr for card in parser.cards if card.active), None)
    credit_balance = _parse_credit_balance(html)

    company_match = COMPANY_PATTERN.search(html)
    company_name = _clean_html_text(company_match.group(1)) if company_match else None

    status_date_match = STATUS_DATE_PATTERN.search(_clean_html_text(html))
    credit_status_date = status_date_match.group(1) if status_date_match else None

    return _ParsedEshopPage(
        cards=parser.cards,
        active_card_id=active_card_id,
        credit_balance=credit_balance,
        company_name=company_name,
        credit_status_date=credit_status_date,
    )


def _parse_credit_balance(html: str) -> Decimal:
    """Parse the active card credit balance."""
    match = CREDIT_PATTERN.search(_clean_html_text(html))
    if match is None:
        raise UbianApiError("Unable to parse Ubian card credit balance.")

    value = match.group(1).replace(" ", "").replace(",", ".")
    return Decimal(value)


def _clean_html_text(value: str) -> str:
    """Return compact text from a small HTML fragment."""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(text)).strip()
