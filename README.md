# Home Assistant FarmBot

An unofficial community integration for connecting FarmBot to Home Assistant through FarmBot's MQTT service and API.

This project is derived from [`sambiam/Farmbot-for-Home-Assistant`](https://github.com/sambiam/Farmbot-for-Home-Assistant) and retains its MIT licence attribution.

## Features

- Sign in with your FarmBot email address and password
- Automatically obtains the FarmBot token, bot ID and MQTT server
- Dynamic switches for peripherals configured in the FarmBot account
- Sequence selector populated from the FarmBot API
- Separate **Run selected sequence** button
- MQTT connected
- Last status received
- Status fresh
- Emergency stop
- Busy
- Fully online

The FarmBot password is used only during sign-in and is not stored by the integration.

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

Enter the same email address and password used for the FarmBot web application. Home Assistant retrieves the remaining connection details automatically.

## Manual installation

Manual installation remains available for development and recovery. Copy `custom_components/farmbot` into the Home Assistant `config/custom_components` directory, restart Home Assistant, then add **FarmBot** through **Settings → Devices & services → Add integration**.

## Project status

Version `0.2.0` targets feature parity with the original community integration while retaining the improved HACS installation, authentication flow and diagnostic entities.

This project is community-maintained and is not an official FarmBot or Home Assistant integration.
