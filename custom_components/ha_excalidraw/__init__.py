"""Intégration Home Assistant : Excalidraw (panneau + relais temps réel)."""
from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import web

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_ICON, PANEL_TITLE, PANEL_URL_PATH
from .relay import ExcalidrawWebSocketView, async_load_persisted_scene

_LOGGER = logging.getLogger(__name__)

WWW_DIR = Path(__file__).parent / "www"


class ExcalidrawAppView(HomeAssistantView):
    """Sert la page HTML du canvas Excalidraw."""

    url = "/api/ha_excalidraw/app"
    name = "api:ha_excalidraw:app"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        html_path = WWW_DIR / "excalidraw-panel.html"
        content = html_path.read_text(encoding="utf-8")
        return web.Response(text=content, content_type="text/html")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Setup YAML (non utilisé, on passe par config_entries)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialise l'intégration à partir d'une config entry (UI)."""
    hass.data.setdefault(DOMAIN, {})

    await async_load_persisted_scene(hass)

    # Si l'intégration est rechargée (bouton "Recharger"), les vues HTTP et
    # le panneau peuvent déjà exister depuis le chargement précédent : on
    # ignore l'erreur plutôt que de faire échouer tout le setup, ce qui
    # casserait la persistance/la collab pour le reste de la session.
    if not hass.data[DOMAIN].get("views_registered"):
        hass.http.register_view(ExcalidrawAppView())
        hass.http.register_view(ExcalidrawWebSocketView(hass))
        hass.data[DOMAIN]["views_registered"] = True

    try:
        async_register_built_in_panel(
            hass,
            component_name="iframe",
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_URL_PATH,
            config={"url": "/api/ha_excalidraw/app"},
            require_admin=False,
        )
    except ValueError:
        _LOGGER.debug("Panneau Excalidraw déjà enregistré, on continue.")

    _LOGGER.info("Panneau Excalidraw enregistré sur /%s", PANEL_URL_PATH)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge l'intégration proprement."""
    from homeassistant.components.frontend import async_remove_panel

    async_remove_panel(hass, PANEL_URL_PATH)
    # On ne fait PAS hass.data.pop(DOMAIN, None) ici : ça effacerait la
    # dernière scène en mémoire et la liste des clients connectés à chaque
    # "Recharger" de l'intégration, ce qui donnait l'impression que le
    # dessin était perdu alors que Home Assistant n'avait même pas redémarré.
    return True
