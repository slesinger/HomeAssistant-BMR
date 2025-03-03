"""Support for BMR shutter blinds - shutters etc."""

# from pyoverkiz.enums import OverkizCommand, UIClass

# from homeassistant.config_entries import ConfigEntry
# from homeassistant.const import Platform
# from homeassistant.core import HomeAssistant
# from homeassistant.helpers.entity_platform import AddEntitiesCallback

# from . import HomeAssistantOverkizData
# from .const import DOMAIN
# from .cover_entities.awning import Awning
# from .cover_entities.generic_cover import OverkizGenericCover
# from .cover_entities.vertical_cover import LowSpeedCover, VerticalCover


from homeassistant.components.cover import CoverEntity

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the BMR covers from a config entry."""
    data: HomeAssistantOverkizData = hass.data[DOMAIN][entry.entry_id]

    entities: list[BmrCover] = [
        VerticalCover(device.device_url, data.coordinator)
        for device in data.platforms[Platform.COVER]
        if device.ui_class != UIClass.AWNING
    ]

    async_add_entities(entities)



    CoverEntityFeature = OPEN | CLOSE | SET_POSITION | OPEN_TILT | CLOSE_TILT | SET_TILT_POSITION
    current_cover_position:int|None = None
    current_cover_tilt_position:int|None = None
    is_closed:bool|None = False  # Required
    klas = CoverDeviceClass.SHUTTER
    stejts = STATE_OPEN, STATE_CLOSED

    def update():
        pass
    
    def async_update():
        pass















class BmrCover(CoverEntity):
    # Implement one of these methods.

    def open_cover(self, **kwargs):
        """Open the cover."""

    async def async_open_cover(self, **kwargs):
        """Open the cover."""

class BmrCover(CoverEntity):
    # Implement one of these methods.

    def close_cover(self, **kwargs):
        """Close cover."""

    async def async_close_cover(self, **kwargs):
        """Close cover."""

class BmrCover(CoverEntity):
    # Implement one of these methods.

    def set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""

class BmrCover(CoverEntity):
    # Implement one of these methods.

    def open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""

    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""

class BmrCover(CoverEntity):
    # Implement one of these methods.

    def close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""

class BmrCover(CoverEntity):
    # Implement one of these methods.

    def set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position."""

    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position."""

