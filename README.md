# Excalidraw pour Home Assistant (via HACS)

Portage de [`addon-excalidraw`](https://github.com/iamer/addon-excalidraw) sous forme
d'**intégration HACS native**, avec collaboration temps réel, mais **sans conteneur
Docker séparé**.

## Ce que fait cette intégration

- Ajoute un panneau **Excalidraw** dans la barre latérale de Home Assistant.
- Le canvas de dessin est chargé côté navigateur depuis un CDN public (esm.sh).
- La collaboration temps réel entre plusieurs appareils est assurée par un petit
  relais WebSocket qui tourne **directement dans le processus Home Assistant**
  (module `relay.py`, basé sur `aiohttp`, déjà utilisé en interne par HA).
- La dernière scène dessinée est sauvegardée dans `config/ha_excalidraw_scene.json`
  et rechargée automatiquement au démarrage.

## Différences avec l'add-on original

| | Add-on Docker original | Cette intégration HACS |
|---|---|---|
| Installation | Supervisor, conteneur séparé | HACS, dans HA Core |
| Fonctionnement hors-ligne | ✅ tout est embarqué | ❌ nécessite un accès internet du **navigateur** (chargement du canvas depuis un CDN) |
| Collaboration temps réel | `excalidraw-room` (Node) | Relais WebSocket maison, en Python, dans HA |
| Persistance | Dans le volume du conteneur | Fichier JSON dans `config/` |
| Compatible Home Assistant Cloud / OS restreint | Non (nécessite Supervisor) | Oui (fonctionne aussi sur HA Core / Container) |

⚠️ **Si vous avez besoin d'un fonctionnement 100 % local/hors-ligne**, gardez plutôt
l'add-on Docker original : cette intégration a fait le choix de charger Excalidraw
depuis un CDN pour rester légère et 100 % installable via HACS (pas de build front à
embarquer, pas de binaire).

## Installation

1. Dans HACS → menu (⋮) → **Dépôts personnalisés**.
2. Ajoutez l'URL de votre fork de ce dépôt, catégorie **Intégration**.
3. Recherchez **Excalidraw** dans HACS et installez-le.
4. Redémarrez Home Assistant.
5. Allez dans **Paramètres → Appareils et services → Ajouter une intégration**,
   cherchez **Excalidraw**, validez (aucun paramètre requis).
6. Le panneau apparaît dans la barre latérale.

## Limitations connues / pistes d'amélioration

- Le relais ne gère pas plusieurs "salles" (rooms) distinctes : tous les clients
  connectés à votre instance HA partagent la même scène — parfaitement adapté à un
  usage familial/domestique, moins à un usage multi-tableaux.
- Pas de gestion fine des conflits d'édition simultanée (dernier écrit gagne),
  contrairement au CRDT plus poussé d'`excalidraw-room`.
- Les versions d'Excalidraw/React chargées depuis le CDN sont figées dans
  `www/excalidraw-panel.html` (`@excalidraw/excalidraw@0.17.6`) : à mettre à jour
  manuellement selon les nouvelles versions publiées.
