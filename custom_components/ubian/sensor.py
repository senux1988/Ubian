"""Sensor platform for Ubian."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfCurrency
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import UbianCard
from .const import (
    ATTR_CARD_ID,
    ATTR_CARD_NUMBER,
    ATTR_COMPANY_NAME,
    ATTR_CREDIT_BALANCE,
    ATTR_CREDIT_STATUS_DATE,
    ATTR_DESCRIPTION,
    ATTR_WAS_ACTIVE_ON_UPDATE,
    DOMAIN,
)
from .coordinator import UbianDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubian sensors from a config entry."""
    coordinator: UbianDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_cards: set[str] = set()

    def add_new_card_entities() -> None:
        new_entities = []
        for card in coordinator.data or []:
            if card.card_id in known_cards:
                continue

            known_cards.add(card.card_id)
            new_entities.append(UbianCardCreditSensor(coordinator, entry, card))

        if new_entities:
            async_add_entities(new_entities)

    add_new_card_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_card_entities))


class UbianCardCreditSensor(
    CoordinatorEntity[UbianDataUpdateCoordinator], SensorEntity
):
    """Sensor representing credit balance on one Ubian card."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = UnitOfCurrency.EURO

    def __init__(
        self,
        coordinator: UbianDataUpdateCoordinator,
        entry: ConfigEntry,
        card: UbianCard,
    ) -> None:
        """Initialize the card sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._card_id = card.card_id
        self._attr_unique_id = f"{entry.entry_id}_{card.card_id}_credit_balance"
        self._attr_translation_key = "card_credit_balance"

    @property
    def _card(self) -> UbianCard | None:
        """Return current card data for this sensor."""
        for card in self.coordinator.data or []:
            if card.card_id == self._card_id:
                return card
        return None

    @property
    def native_value(self) -> Decimal | None:
        """Return the current credit balance."""
        card = self._card
        if card is None:
            return None
        return card.credit_balance

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return card attributes."""
        card = self._card
        if card is None:
            return None

        return {
            ATTR_CARD_ID: card.card_id,
            ATTR_CARD_NUMBER: card.raw.get(ATTR_CARD_NUMBER),
            ATTR_COMPANY_NAME: card.raw.get(ATTR_COMPANY_NAME),
            ATTR_DESCRIPTION: card.description,
            ATTR_CREDIT_BALANCE: str(card.credit_balance),
            ATTR_CREDIT_STATUS_DATE: card.raw.get(ATTR_CREDIT_STATUS_DATE),
            ATTR_WAS_ACTIVE_ON_UPDATE: card.raw.get("active"),
        }

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information for this Ubian card."""
        card = self._card
        name = card.description if card is not None else self._card_id

        return {
            "identifiers": {(DOMAIN, self._card_id)},
            "name": name,
            "manufacturer": "Ubian",
            "entry_type": "service",
        }
