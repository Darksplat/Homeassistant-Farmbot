# Home Assistant FarmBot

Early custom integration for connecting FarmBot to Home Assistant through FarmBot's MQTT service.

## Initial diagnostic entities

- MQTT connected
- Last status received
- Status fresh
- Emergency stop
- Busy
- Fully online

The integration retains the existing FarmBot token-refresh and RPC command helpers for later command entities and services.

## Manual installation

Copy `custom_components/farmbot` into the Home Assistant `config/custom_components` directory, restart Home Assistant, then add **FarmBot** through **Settings → Devices & services → Add integration**.

The initial config flow requires:

- Encoded FarmBot token
- FarmBot device ID
- MQTT host supplied with the FarmBot token

## Status

This is an initial development version and should be tested on a non-critical Home Assistant installation before general release.
