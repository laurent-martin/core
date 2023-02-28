"""Sensor for Suez Water Consumption data."""
from __future__ import annotations

import copy
from datetime import timedelta
import logging

from toutsurmoneau.toutsurmoneau import ToutSurMonEau
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, UnitOfVolume
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

# (used by class EntityComponent) data is updated daily during the night
SCAN_INTERVAL = timedelta(hours=12)

# optional config param to specify meter identifier
CONF_METER_ID = "counter_id"

# config parameters
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_METER_ID, default=""): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform.

    Called by class EntityPlatform.
    """
    try:
        client = ToutSurMonEau(
            username=config[CONF_USERNAME],
            password=config[CONF_PASSWORD],
            meter_id=config[CONF_METER_ID],
            use_litre=True,
            compatibility=False,
        )

        if not client.check_credentials():
            _LOGGER.warning("Login to Suez portal failed.")
            return

        add_entities([SuezSensor(client)], True)
    except Exception as e:
        _LOGGER.warning(f"Unable to create Suez Client: {e}")
        return


class SuezSensor(SensorEntity):
    """The sensor that read information from the Suez portal.

    Note that there is a minimum 1 day delay between returned value and actual reading date.
    """

    def __init__(self, client: ToutSurMonEau) -> None:
        """Initialize the data object."""
        self.client = client
        self._attr_name = "Suez Water Meter"
        self._attr_icon = "mdi:water-pump"
        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_extra_state_attributes = {}

    def update(self) -> None:
        """Update with latest collected data from Suez subscriber portal."""
        try:
            self.client.update()
            # _state holds the volume of consumed water during previous day
            self._attr_native_value = self.client.state
            self._attr_available = True
            self._attr_attribution = self.client.attributes["attribution"]
            self._attr_extra_state_attributes = copy.deepcopy(self.client.attributes)
            _LOGGER.debug("Suez state is: %s", self.native_value)
        except Exception as e:
            self._attr_available = False
            _LOGGER.warning(f"Unable to update data: {e}")
