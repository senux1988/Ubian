"""Sensor platform for Ubian."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import UbianCard
from .const import (
    ATTR_CARD_ID,
    ATTR_CARD_NUMBER,
    ATTR_CARD_TYPE,
    ATTR_CARD_VALIDITY,
    ATTR_COMPANY_NAME,
    ATTR_CREDIT_BALANCE,
    ATTR_CREDIT_STATUS_DATE,
    ATTR_DESCRIPTION,
    ATTR_DISCOUNT_VALIDITY,
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
            new_entities.extend(
                UbianCardSensor(coordinator, entry, card, description)
                for description in SENSOR_DESCRIPTIONS
            )

        if new_entities:
            async_add_entities(new_entities)

    add_new_card_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_card_entities))


@dataclass(frozen=True, slots=True)
class UbianSensorDescription(SensorEntityDescription):
    """Describe an Ubian card sensor."""

    value_fn: Callable[[UbianCard], Any] = field(default=lambda card: None)


SENSOR_DESCRIPTIONS: tuple[UbianSensorDescription, ...] = (
    UbianSensorDescription(
        key=ATTR_CREDIT_BALANCE,
        translation_key="card_credit_balance",
        value_fn=lambda card: card.credit_balance,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
    ),
    UbianSensorDescription(
        key=ATTR_CARD_VALIDITY,
        translation_key="card_validity",
        value_fn=lambda card: _parse_date(card.raw.get(ATTR_CARD_VALIDITY)),
        device_class=SensorDeviceClass.DATE,
    ),
    UbianSensorDescription(
        key=ATTR_CARD_TYPE,
        translation_key="card_type",
        value_fn=lambda card: card.raw.get(ATTR_CARD_TYPE),
    ),
    UbianSensorDescription(
        key=ATTR_DISCOUNT_VALIDITY,
        translation_key="discount_validity",
        value_fn=lambda card: _parse_date(card.raw.get(ATTR_DISCOUNT_VALIDITY)),
        device_class=SensorDeviceClass.DATE,
    ),
)


class UbianCardSensor(
    CoordinatorEntity[UbianDataUpdateCoordinator], SensorEntity
):
    """Sensor representing one value for an Ubian card."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: UbianDataUpdateCoordinator,
        entry: ConfigEntry,
        card: UbianCard,
        description: UbianSensorDescription,
    ) -> None:
        """Initialize the Ubian card sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._card_id = card.card_id
        self._attr_unique_id = f"{entry.entry_id}_{card.card_id}_{description.key}"
        self._attr_translation_key = description.translation_key
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement

    @property
    def _card(self) -> UbianCard | None:
        """Return current card data for this sensor."""
        for card in self.coordinator.data or []:
            if card.card_id == self._card_id:
                return card
        return None

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        card = self._card
        if card is None:
            return None
        return self.entity_description.value_fn(card)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return card attributes."""
        card = self._card
        if card is None:
            return None

        return {
            ATTR_CARD_ID: card.card_id,
            ATTR_CARD_NUMBER: card.raw.get(ATTR_CARD_NUMBER),
            ATTR_CARD_TYPE: card.raw.get(ATTR_CARD_TYPE),
            ATTR_CARD_VALIDITY: card.raw.get(ATTR_CARD_VALIDITY),
            ATTR_COMPANY_NAME: card.raw.get(ATTR_COMPANY_NAME),
            ATTR_DESCRIPTION: card.description,
            ATTR_CREDIT_BALANCE: str(card.credit_balance),
            ATTR_CREDIT_STATUS_DATE: card.raw.get(ATTR_CREDIT_STATUS_DATE),
            ATTR_DISCOUNT_VALIDITY: card.raw.get(ATTR_DISCOUNT_VALIDITY),
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


def _parse_date(value: str | None) -> date | None:
    """Parse Ubian date value."""
    if not value:
        return None

    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None
