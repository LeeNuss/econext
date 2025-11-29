"""Base entity for ecoNET Next integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import EconetNextCoordinator


class EconetNextEntity(CoordinatorEntity[EconetNextCoordinator]):
    """Base entity for ecoNET Next."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EconetNextCoordinator,
        param_id: str,
        device_id: str | None = None,
    ) -> None:
        """Initialize the entity.

        Args:
            coordinator: The data coordinator.
            param_id: The parameter ID this entity represents.
            device_id: Optional device identifier suffix (e.g., "dhw", "circuit-1").
                      If None, entity belongs to the main controller device.

        """
        super().__init__(coordinator)
        self._param_id = param_id
        self._device_id = device_id

        # Build unique_id
        uid = coordinator.get_device_uid()
        if device_id:
            self._attr_unique_id = f"{uid}_{device_id}_{param_id}"
        else:
            self._attr_unique_id = f"{uid}_{param_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        uid = self.coordinator.get_device_uid()
        device_name = self.coordinator.get_device_name()

        if self._device_id:
            # Sub-device (DHW, Buffer, Circuit, Heat Pump)
            device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{uid}_{self._device_id}")},
                name=self._get_sub_device_name(),
                manufacturer=MANUFACTURER,
                via_device=(DOMAIN, uid),
            )
            # Add model for circuits
            if self._device_id.startswith("circuit_"):
                circuit_num = self._device_id.split("_")[1]
                device_info["model"] = f"Circuit {circuit_num}"
            return device_info

        # Main controller device
        return DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name=device_name,
            manufacturer=MANUFACTURER,
            model="ecoMAX360i",
            sw_version=self.coordinator.get_param_value(0),  # PS - software version
            hw_version=self.coordinator.get_param_value(1),  # HV - hardware version
        )

    def _get_sub_device_name(self) -> str:
        """Get the name for a sub-device."""
        if not self._device_id:
            return self.coordinator.get_device_name()

        if self._device_id == "dhw":
            return "DHW"
        if self._device_id == "buffer":
            return "Buffer"
        if self._device_id == "heatpump":
            return "Heat Pump"
        if self._device_id.startswith("circuit_"):
            circuit_num = self._device_id.split("_")[1]
            # Circuit name param IDs: 278, 328, 900, 986, 1037, 780, 830
            name_params = {
                "1": "278",
                "2": "328",
                "3": "900",
                "4": "986",
                "5": "1037",
                "6": "780",
                "7": "830",
            }
            if circuit_num in name_params:
                name_param = self.coordinator.get_param(name_params[circuit_num])
                if name_param:
                    custom_name = name_param.get("value", "").strip()
                    if custom_name:
                        return custom_name
            return f"Circuit {circuit_num}"

        return self._device_id

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self._is_value_valid()

    def _is_value_valid(self) -> bool:
        """Check if the parameter value is valid.

        Override in subclasses for specific validation (e.g., temp != 999.0).
        """
        return self.coordinator.get_param(self._param_id) is not None

    def _get_param_value(self):
        """Get the current parameter value."""
        return self.coordinator.get_param_value(self._param_id)

    def _get_param(self) -> dict | None:
        """Get the full parameter dict."""
        return self.coordinator.get_param(self._param_id)
