"""
Cover Platform Device for Wiser.
https://github.com/asantaga/wiserHomeAssistantPlatform
Angelosantagata@gmail.com
"""
from functools import partial

import voluptuous as vol



from homeassistant.components.cover import (
    SUPPORT_OPEN,
    SUPPORT_CLOSE,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    STATE_CLOSED,
    STATE_OPEN,
    STATE_CLOSING,
    STATE_OPENING,
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    CoverEntity
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect


from .const import (
    DATA,
    DOMAIN,
    MANUFACTURER,
    ROOM,
    WISER_SERVICES
)
from .helpers import get_device_name, get_identifier, get_room_name, get_unique_id

import logging


MANUFACTURER='Schneider Electric'

_LOGGER = logging.getLogger(__name__)

ATTR_COPYTO_ENTITY_ID = "to_entity_id"
ATTR_FILENAME = "filename"


SUPPORT_FLAGS =  SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION | SUPPORT_STOP

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Wiser shutter device."""

    data = hass.data[DOMAIN][config_entry.entry_id][DATA]  # Get Handler

    wiser_shutters = []
    if data.wiserhub.devices.shutters:
        _LOGGER.debug("Setting up shutter entities")
        for shutter in data.wiserhub.devices.shutters.all :
            if shutter.product_type=="Shutter":
                wiser_shutters.append ( 
                    WiserShutter(data, shutter.id ) 
                )
        async_add_entities(wiser_shutters, True)       

    # Setup services
    """
    platform = entity_platform.async_get_current_platform()



    platform.async_register_entity_service(
        WISER_SERVICES["SERVICE_GET_SHUTTER_SCHEDULE"],
            {
                vol.Optional(ATTR_FILENAME, default=""): vol.Coerce(str),
            },
            "async_get_schedule"
        )

    platform.async_register_entity_service(
        WISER_SERVICES["SERVICE_SET_SHUTTER_SCHEDULE"],
            {
                vol.Optional(ATTR_FILENAME, default=""): vol.Coerce(str),
            },
            "async_set_schedule"
        )

    platform.async_register_entity_service(
        WISER_SERVICES["SERVICE_COPY_SHUTTER_SCHEDULE"],
            {
                vol.Required(ATTR_COPYTO_ENTITY_ID): cv.entity_id,
            },
            "async_copy_schedule"
        )
    """

class WiserShutter(CoverEntity):
    """Wisershutter ClientEntity Object."""

    def __init__(self, data, shutter_id):
        """Initialize the sensor."""
        self._data = data
        self._shutter_id = shutter_id
        self._shutter = self._data.wiserhub.devices.shutters.get_by_id(self._shutter_id)
        self._name = self._shutter.name

        _LOGGER.info(f"{self._data.wiserhub.system.name} {self._name} init")

    async def async_force_update(self):
        _LOGGER.debug(f"{self._name} requested hub update")
        await self._data.async_update(no_throttle=True)

    async def async_update(self):
        """Async update method."""
        self._shutter = self._data.wiserhub.devices.shutters.get_by_id(self._shutter_id)
      
    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_FLAGS
    
    @property
    def current_cover_position(self):
        """Return current position from data."""
        return self._shutter.current_lift

    def stop_cover(self, **kwargs):
        """Stop the shutter"""
        self._shutter.stop()

    @property
    def is_closed(self):
        return self._shutter.is_closed

    @property
    def is_opening(self):
        """Return if the shutter is opening or not."""
        return self._shutter.is_opening

    @property
    def is_closing(self):
        """Return if the shutter is closing or not."""
        return self._shutter.is_closing

    def open_cover(self, **kwargs):
        """Open the cover."""
        self._shutter.open()

    def close_cover(self, **kwargs):
        """Close cover."""
        self._shutter.close()

    def set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs[ATTR_POSITION]
        self._shutter.current_lift = position

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
                "name": get_device_name(self._data, self._shutter_id),
                "identifiers": {(DOMAIN, get_identifier(self._data, self._shutter_id))},
                "manufacturer": MANUFACTURER,
                "model": self._shutter.product_type,
                "sw_version": self._shutter.firmware_version,
                "via_device": (DOMAIN, self._data.wiserhub.system.name),
            }

    @property
    def icon(self):
        """Return icon to show if shutter is closed or Open."""
        return "mdi:window-shutter" if self.is_closed else "mdi:window-shutter-open"

    @property
    def name(self):
        """Return Name of device."""
        return f"{get_device_name(self._data, self._shutter_id)}"   
    
    @property
    def should_poll(self):
        """We don't want polling so return false."""
        return False

    @property
    def shutter_unit(self):
        """Return percent units."""
        return "%"

    @property
    def unique_id(self):
        """Return unique Id."""
        return f"{self._data.wiserhub.system.name}-Wisershutter-{self._shutter_id}-{self.name}"
        
    @property
    def extra_state_attributes(self):
        """Return state attributes."""
        # Generic attributes
        attrs = super().state_attributes
        attrs["name"] = self._shutter.name
        attrs["shutter_id"] = self._shutter_id

        attrs["mode"] = self._shutter.mode
       
        attrs["control_source"] = self._shutter.control_source
        attrs["is_open"] = self._shutter.is_open
        attrs["is_closed"] = self._shutter.is_closed
        if self._shutter.is_open :
            attrs["current_state"] = "Open"
        elif  self._shutter.is_closed :
            attrs["current_state"] ="Closed"
        elif (self._shutter.is_open == False and self._shutter.is_closed == False):
            attrs["current_state"] = "Middle" 
        attrs["current_lift"] = self._shutter.current_lift
        attrs["manual_lift"] = self._shutter.manual_lift
        attrs["target_lift"] = self._shutter.target_lift
        attrs["scheduled_lift"] = self._shutter.scheduled_lift
        attrs["lift_movement"] = self._shutter.lift_movement
        attrs["is_open"] = self._shutter.is_open
        attrs["is_closed"] = self._shutter.is_closed
        attrs["lift_open_time"] = self._shutter.drive_config.open_time
        attrs["lift_close_time"] = self._shutter.drive_config.close_time
        attrs["schedule_id"] = self._shutter.schedule_id
        
        if  self._data.wiserhub.rooms.get_by_id(self._shutter.room_id) is not None:
            attrs["room"] = self._data.wiserhub.rooms.get_by_id(self._shutter.room_id).name
        else:
            attrs["room"] = "Unassigned"     
        
        if self._shutter.schedule:
            attrs["next_schedule_change"] = str(self._shutter.schedule.next.time)
            attrs["next_schedule_state"] = self._shutter.schedule.next.setting    
            
            
        return attrs

    """
    @callback
    async def async_get_schedule(self, filename: str) -> None:
        try:
            if self._shutter.schedule:
                _LOGGER.info(f"Saving {self._shutter.name} schedule to file {filename}")
                await self.hass.async_add_executor_job(
                    self._shutter.schedule.save_schedule_to_yaml_file, filename
                    )
            else:
                _LOGGER.warning(f"{self._shutter.name} has no schedule to save")	
        except:
            _LOGGER.error(f"Saving {self._shutter.name} schedule to file {filename}")

    @callback
    async def async_set_schedule(self, filename: str) -> None:
        try:
            if self._shutter.schedule:
                _LOGGER.info(f"Setting {self._shutter.name} schedule from file {filename}")
                await self.hass.async_add_executor_job(
                    self._shutter.schedule.set_schedule_from_yaml_file, filename
                    )
                await self.async_force_update()
            else:
                _LOGGER.warning(f"{self._shutter.name} has no schedule to assign")
				
        except:
            _LOGGER.error(f"Error setting {self._shutter.name} schedule from file {filename}")

    @callback
    async def async_copy_schedule(self, to_entity_id)-> None:
        to_shutter_name = to_entity_id.replace("shutter.wiser_","").replace("_"," ")
        try:
            if self._shutter.schedule:
                # Add Check that to_entity is of same type as from_entity
                _LOGGER.info(f"Copying schedule from {self._shutter.name} to {to_shutter_name.title()}")
                await self.hass.async_add_executor_job(
                    self._shutter.schedule.copy_schedule, self._data.wiserhub.shutters.get_by_name(to_room_name).schedule.id
                    )
                await self.async_force_update()
            else:
                _LOGGER.warning(f"{self._shutter.name} has no schedule to copy")	
        except:
            _LOGGER.error(f"Error copying schedule from {self._shutter.name} to {to_shutter_name}")
    """

    async def async_added_to_hass(self):
        """Subscribe for update from the hub."""
        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{self._data.wiserhub.system.name}-HubUpdateMessage", async_update_state
            )
        )