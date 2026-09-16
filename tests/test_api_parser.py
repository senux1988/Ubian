"""Tests for the Ubian HTML parser."""

from __future__ import annotations

from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types


def _load_api_module():
    """Load api.py without requiring Home Assistant test dependencies."""
    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientSession = object
    sys.modules["aiohttp"] = aiohttp

    module_path = Path(__file__).parents[1] / "custom_components" / "ubian" / "api.py"
    spec = spec_from_file_location("ubian_api", module_path)
    module = module_from_spec(spec)
    sys.modules["ubian_api"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_eshop_page_cards_and_active_credit() -> None:
    """Parse cards and active card balance from Ubian e-shop HTML."""
    api = _load_api_module()

    page = api._parse_eshop_page(
        """
        <ul class="dropdown-menu dropdown-cards">
            <li class="current-card">
                <a class="js-set-active-card" data-snr="111">
                    <span class="title-label">Primary Card&nbsp;</span>
                    <span class="card-no">1 1111 1111</span>
                </a>
            </li>
            <li>
                <a class="js-set-active-card" data-snr="222">
                    <span class="title-label">Secondary Card&nbsp;</span>
                    <span class="card-no">2 2222 2222</span>
                </a>
            </li>
        </ul>
        <span class="company-name long">ARRIVA Test</span>
        <span class="big">Kredit 12,34 €</span>
        <span style="font-size: 12px">Stav k 16.09.2026</span>
        """
    )

    assert page.active_card_id == "111"
    assert page.credit_balance == Decimal("12.34")
    assert page.company_name == "ARRIVA Test"
    assert page.credit_status_date == "16.09.2026"
    assert [card.snr for card in page.cards] == ["111", "222"]
    assert page.cards[0].description == "Primary Card"
    assert page.cards[0].card_number == "1 1111 1111"
    assert page.cards[0].active is True
    assert page.cards[1].active is False
