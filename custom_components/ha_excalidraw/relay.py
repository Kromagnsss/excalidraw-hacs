"""Relais WebSocket temps réel pour la collaboration Excalidraw.

Ce module remplace le serveur Node "excalidraw-room" de l'add-on original.
Il tourne directement dans le event loop de Home Assistant (aiohttp),
sans dépendance externe.

Protocole (maison, volontairement simple) :
  Client -> Serveur : {"type": "update", "payload": {...scène...}}
  Serveur -> Client (nouveau client) : {"type": "init", "payload": {...dernière scène connue...}}
  Serveur -> Clients (broadcast) : {"type": "update", "payload": {...}}
"""
from __future__ import annotations

import json
import logging

from aiohttp import web, WSMsgType

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN, STORAGE_FILE

_LOGGER = logging.getLogger(__name__)


class ExcalidrawWebSocketView(HomeAssistantView):
    """Vue HTTP qui gère l'upgrade WebSocket et le relais de messages."""

    url = "/api/ha_excalidraw/ws"
    name = "api:ha_excalidraw:ws"
    requires_auth = False  # Le panneau est déjà derrière l'auth HA (iframe interne)

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        store = hass.data.setdefault(DOMAIN, {})
        store.setdefault("clients", set())
        store.setdefault("last_scene", None)

    async def get(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)

        store = self.hass.data[DOMAIN]
        clients: set[web.WebSocketResponse] = store["clients"]
        clients.add(ws)
        _LOGGER.debug("Client Excalidraw connecté (%d au total)", len(clients))

        # Envoie l'état actuel de la scène au nouveau client, s'il existe
        if store["last_scene"] is not None:
            await ws.send_json({"type": "init", "payload": store["last_scene"]})

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_message(ws, clients, store, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    _LOGGER.warning(
                        "Erreur WebSocket Excalidraw: %s", ws.exception()
                    )
        finally:
            clients.discard(ws)
            _LOGGER.debug("Client Excalidraw déconnecté (%d restants)", len(clients))

        return ws

    async def _handle_message(
        self,
        sender: web.WebSocketResponse,
        clients: set[web.WebSocketResponse],
        store: dict,
        raw: str,
    ) -> None:
        try:
            data = json.loads(raw)
        except ValueError:
            return

        if data.get("type") != "update":
            return

        payload = data.get("payload")
        if payload is None:
            return

        store["last_scene"] = payload
        self._schedule_persist(payload)

        # Diffuse aux autres clients connectés (pas à l'émetteur)
        stale: list[web.WebSocketResponse] = []
        for client in clients:
            if client is sender or client.closed:
                if client.closed:
                    stale.append(client)
                continue
            try:
                await client.send_json({"type": "update", "payload": payload})
            except ConnectionResetError:
                stale.append(client)

        for client in stale:
            clients.discard(client)

    def _schedule_persist(self, payload: dict) -> None:
        """Persiste la dernière scène sur disque, sans bloquer la boucle."""
        path = self.hass.config.path(STORAGE_FILE)

        def _write() -> None:
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle)
            except OSError as err:
                _LOGGER.warning("Impossible d'enregistrer la scène Excalidraw: %s", err)

        self.hass.async_add_executor_job(_write)


async def async_load_persisted_scene(hass: HomeAssistant) -> None:
    """Recharge la dernière scène connue depuis le disque au démarrage."""
    path = hass.config.path(STORAGE_FILE)

    def _read() -> dict | None:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return None

    scene = await hass.async_add_executor_job(_read)
    if scene is not None:
        hass.data.setdefault(DOMAIN, {})["last_scene"] = scene
