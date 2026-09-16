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
        <ul class="infolist">
            <li class="item">
                <strong>Platnosť karty</strong>
                <p><span>19.09.2030</span></p>
            </li>
            <li class="item">
                <strong>Typ karty</strong>
                <p>Deti od 6 do 18 rokov</p>
            </li>
            <li class="item">
                <strong>Platnosť zľavy</strong>
                <p><span>19.09.2030</span></p>
            </li>
        </ul>
        """
    )

    assert page.active_card_id == "111"
    assert page.credit_balance == Decimal("12.34")
    assert page.company_name == "ARRIVA Test"
    assert page.credit_status_date == "16.09.2026"
    assert page.card_validity == "19.09.2030"
    assert page.card_type == "Deti od 6 do 18 rokov"
    assert page.discount_validity == "19.09.2030"
    assert [card.snr for card in page.cards] == ["111", "222"]
    assert page.cards[0].description == "Primary Card"
    assert page.cards[0].card_number == "1 1111 1111"
    assert page.cards[0].active is True
    assert page.cards[1].active is False


def test_parse_transactions_page() -> None:
    """Parse latest transactions from Ubian transactions HTML."""
    api = _load_api_module()

    transactions = api._parse_transactions_page(
        """
        <table class="new-layout transactions">
            <tbody>
                <tr>
                    <td class="datetime">
                        <span class="hidden-mobile">15. 09. 2026</span>
                        <span class="visible-mobile">15.09</span>
                        <span class="vertical-line">|</span>
                        <span>20:00</span>
                    </td>
                    <td class="green">
                        <span class="mobile_td_bold mobile_block">Dobitie kreditu</span>
                        <span class="vertical-line">|</span>
                        ARRIVA Nitra
                    </td>
                    <td><span class="mobile_block visible-mobile"></span></td>
                    <td class="mobile_price_pdf">
                        <span class="green">10,00&nbsp;€</span>
                        <div class="pdf_block">
                            <a href="/transactions/pdf/4-14268050.pdf" class="download">
                                <span class="icon icon-download"></span>
                            </a>
                        </div>
                    </td>
                </tr>
                <tr>
                    <td class="datetime">
                        <span class="hidden-mobile">14. 09. 2026</span>
                        <span class="visible-mobile">14.09</span>
                        <span class="vertical-line">|</span>
                        <span>14:41</span>
                    </td>
                    <td class="">
                        <span class="mobile_td_bold mobile_block">Jazda</span>
                        <span class="vertical-line">|</span>
                        ARRIVA Nitra
                    </td>
                    <td><span class="mobile_block visible-mobile"></span></td>
                    <td class="mobile_price_pdf">
                        <span class="red">-0,63&nbsp;€</span>
                    </td>
                </tr>
            </tbody>
        </table>
        """
    )

    assert len(transactions) == 2
    assert transactions[0].occurred_at == "2026-09-15T20:00:00"
    assert transactions[0].transaction_type == "Dobitie kreditu"
    assert transactions[0].merchant == "ARRIVA Nitra"
    assert transactions[0].amount == Decimal("10.00")
    assert (
        transactions[0].pdf_url
        == "https://www.ubian.sk/transactions/pdf/4-14268050.pdf"
    )
    assert transactions[1].transaction_type == "Jazda"
    assert transactions[1].amount == Decimal("-0.63")
