"""Support for Wiser lights vis Wiser Hub"""
import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect


from .const import DATA, DOMAIN, MANUFACTURER
from .helpers import get_device_name, get_identifier, get_unique_id

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Wiser System Switch entities."""
    data = hass.data[DOMAIN][config_entry.entry_id][DATA]  # Get Handler

    wiser_lights = []
    if data.wiserhub.devices.lights:
        _LOGGER.debug("Setting up light entities")
        for light in data.wiserhub.devices.lights.all:
            if light.is_dimmable:
                wiser_lights.append(
                    WiserDimmerLight(data, light.id)
                )
        async_add_entities(wiser_lights, True)


class WiserLight(LightEntity):
    def __init__(self, data, light_id):
        """Initialize the sensor."""
        self._data = data
        self._light_id = light_id
        self._light = self._data.wiserhub.devices.lights.get_by_id(light_id)
        self._name = self._light.name
        _LOGGER.info(f"{self._data.wiserhub.system.name} {self._name} init")

    async def async_force_update(self):
        await self._data.async_update(no_throttle=True)

    async def async_update(self):
        """Async Update to HA."""
        _LOGGER.debug(f"Wiser {self.name} Light Update requested")
        self._light = self._data.wiserhub.devices.lights.get_by_id(self._light_id)

    @property
    def is_on(self):
        """Return the boolean response if the node is on."""
        return self._light.is_on

    @property
    def name(self):
        """Return the name of the Device."""
        return f"{get_device_name(self._data, self._light.id)} {self._name}"

    @property
    def icon(self):
        """Return icon."""
        if self._light.mode == "Auto":
            return "mdi:lightbulb-auto" if self.is_on else "mdi:lightbulb-auto-outline"
        else:
            return "mdi:lightbulb" if self.is_on else "mdi:lightbulb-outline"

    @property
    def unique_id(self):
        return get_unique_id(self._data, "device", "light", self.name)

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
                "name": get_device_name(self._data, self._light.id),
                "identifiers": {(DOMAIN, get_identifier(self._data, self._light.id))},
                "manufacturer": MANUFACTURER,
                "model": "NHPDimmer",   #This needs api update
                "sw_version": "020519ff",   #This needs api update
                "via_device": (DOMAIN, self._data.wiserhub.system.name),
            }

    @property
    def extra_state_attributes(self):
        """Return state attributes."""
        attrs = {}
        return attrs

    async def async_added_to_hass(self):
        """Subscribe for update from the hub."""

        async def async_update_state():
            """Update light state."""
            await self.async_update_ha_state(True)

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{self._data.wiserhub.system.name}-HubUpdateMessage", async_update_state
            )
        )


class WiserDimmerLight(WiserLight):
    """A Class for an Wiser light entity."""
    def __init__(self, data, light_id):
        """Initialize the sensor."""
        super().__init__(data, light_id)

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    @property
    def brightness(self):
        """Return the brightness of this light between 0..100."""
        return round((self._light.current_percentage / 100) * 255)

    async def async_turn_on(self, **kwargs):
        """Turn light on."""
        if ATTR_BRIGHTNESS in kwargs:
            brightness = int(kwargs[ATTR_BRIGHTNESS])
            await self.hass.async_add_executor_job(
                setattr, self._light, "current_percentage", round((brightness / 255) * 100)
            )
        else:
            await self.hass.async_add_executor_job(
                self._light.turn_on
            )
        await self.async_force_update()
        return True

    async def async_turn_off(self, **kwargs):
        """Turn light off."""
        await self.hass.async_add_executor_job(
            self._light.turn_off
        )
        await self.async_force_update()
        return True

    @property
    def extra_state_attributes(self):
        """Return state attributes."""
        attrs = super().extra_state_attributes
        attrs["name"] = self._light.name
        attrs["mode"] = self._light.mode
        attrs["current_state"] = self._light.current_state
        attrs["control_source"] = self._light.control_source
        attrs["current_percentage"] = self._light.current_percentage
        attrs["current_level"] = self._light.current_level
        attrs["is_dimmable"] = self._light.is_dimmable
        attrs["output_range_min"] = self._light.output_range.min
        attrs["output_range_max"] = self._light.output_range.max
        
        if  self._data.wiserhub.rooms.get_by_id(self._light.room_id) is not None:
            attrs["room"] = self._data.wiserhub.rooms.get_by_id(self._light.room_id).name
        else:
            attrs["room"] = "Unassigned"     
        attrs["target_state"] = self._light.target_state
        attrs["target_percentage"] = self._light.target_percentage
        attrs["schedule_id"] = self._light.schedule_id
        if self._light.schedule:
            attrs["next_schedule_change"] = str(self._light.schedule.next.time)
            attrs["next_schedule_percentage"] = self._light.schedule.next.setting    
        return attrs
