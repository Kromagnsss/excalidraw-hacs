"""Config flow pour ha_excalidraw."""
from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN


class ExcalidrawConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Assistant d'ajout : une seule instance, aucun paramètre requis."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Excalidraw", data={})

        return self.async_show_form(step_id="user")
