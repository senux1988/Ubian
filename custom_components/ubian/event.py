"""Event platform for Ubian."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import UbianCard
from .const import (
    ATTR_CARD_ID,
    ATTR_CARD_NUMBER,
    ATTR_DESCRIPTION,
    ATTR_LATEST_TRANSACTION,
    DOMAIN,
    EVENT_TRANSACTION,
)
from .coordinator import UbianDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubian event entities from a config entry."""
    coordinator: UbianDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_cards: set[str] = set()

    def add_new_card_entities() -> None:
        new_entities = []
        for card in coordinator.data or []:
            if card.card_id in known_cards:
                continue

            known_cards.add(card.card_id)
            new_entities.append(UbianTransactionEvent(coordinator, entry, card))

        if new_entities:
            async_add_entities(new_entities)

    add_new_card_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_card_entities))


class UbianTransactionEvent(
    CoordinatorEntity[UbianDataUpdateCoordinator], EventEntity
):
    """Event entity that fires when a card has a new latest transaction."""

    _attr_event_types = [EVENT_TRANSACTION]
    _attr_has_entity_name = True
    _attr_translation_key = "card_transaction"

    def __init__(
        self,
        coordinator: UbianDataUpdateCoordinator,
        entry: ConfigEntry,
        card: UbianCard,
    ) -> None:
        """Initialize the Ubian transaction event entity."""
        super().__init__(coordinator)
        self._card_id = card.card_id
        self._last_transaction_id = _transaction_id(card)
        self._attr_unique_id = f"{entry.entry_id}_{card.card_id}_transaction"

    @property
    def _card(self) -> UbianCard | None:
        """Return current card data for this event entity."""
        for card in self.coordinator.data or []:
            if card.card_id == self._card_id:
                return card
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return transaction event attributes."""
        card = self._card
        if card is None:
            return None

        return {
            ATTR_CARD_ID: card.card_id,
            ATTR_CARD_NUMBER: card.raw.get(ATTR_CARD_NUMBER),
            ATTR_DESCRIPTION: card.description,
            ATTR_LATEST_TRANSACTION: card.raw.get(ATTR_LATEST_TRANSACTION),
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

    def _handle_coordinator_update(self) -> None:
        """Trigger an event when the latest transaction changes."""
        card = self._card
        transaction_id = _transaction_id(card)

        if transaction_id is not None and transaction_id != self._last_transaction_id:
            self._last_transaction_id = transaction_id
            self._trigger_event(
                EVENT_TRANSACTION,
                card.raw.get(ATTR_LATEST_TRANSACTION) or {},
            )

        self.async_write_ha_state()


def _transaction_id(card: UbianCard | None) -> str | None:
    """Return the latest transaction id for a card."""
    if card is None:
        return None

    latest_transaction = card.raw.get(ATTR_LATEST_TRANSACTION)
    if not isinstance(latest_transaction, dict):
        return None

    transaction_id = latest_transaction.get("transaction_id")
    return transaction_id if isinstance(transaction_id, str) else None
