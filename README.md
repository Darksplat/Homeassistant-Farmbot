# Home Assistant FarmBot

An unofficial community integration for connecting FarmBot to Home Assistant through FarmBot's MQTT service and API.

This project is derived from [`sambiam/Farmbot-for-Home-Assistant`](https://github.com/sambiam/Farmbot-for-Home-Assistant) and retains its MIT licence attribution.

## Current entities

- MQTT connected
- Last status received
- Status fresh
- Emergency stop
- Busy
- Fully online

The integration also retains the existing FarmBot token-refresh and RPC command helpers for future command entities and services.

## Install with HACS

Until this repository is accepted into the default HACS catalogue, add it as a custom repository:

1. Open **HACS** in Home Assistant.
2. Select **Integrations**.
3. Open the three-dot menu and select **Custom repositories**.
4. Enter `https://github.com/Darksplat/Homeassistant-Farmbot`.
5. Select **Integration** as the category.
6. Add the repository and install **FarmBot**.
7. Restart Home Assistant.
8. Open **Settings → Devices & services → Add integration** and select **FarmBot**.

## Configuration

The initial config flow requires:

- Encoded FarmBot token
- FarmBot device ID
- MQTT host supplied with the FarmBot token

## Manual installation

Manual installation remains available for development and recovery. Copy `custom_components/farmbot` into the Home Assistant `config/custom_components` directory, restart Home Assistant, then add **FarmBot** through **Settings → Devices & services → Add integration**.

## Project status

This is an early development release and should be tested carefully before being used for critical FarmBot operations.

This project is community-maintained and is not an official FarmBot or Home Assistant integration.
