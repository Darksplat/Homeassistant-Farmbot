# Home Assistant FarmBot

An unofficial community integration for connecting FarmBot to Home Assistant through FarmBot's MQTT service and API.

This project is derived from [`sambiam/Farmbot-for-Home-Assistant`](https://github.com/sambiam/Farmbot-for-Home-Assistant) and retains its MIT licence attribution.

## Features

- Sign in with your FarmBot email address and password
- Automatically obtains the FarmBot token, bot ID and MQTT server
- Dynamic switches for peripherals configured in the FarmBot account
- Sequence selector populated from the FarmBot API
- Separate **Run selected sequence** button
- Home Assistant actions for executing any sequence and moving to absolute XYZ coordinates
- X, Y and Z position sensors
- FarmBot OS/controller version, firmware version, uptime and selected tool slot sensors
- MQTT connected, status fresh, emergency stop, busy and fully online diagnostics
- Sync, emergency stop and unlock command buttons
- Dynamic device metadata from the latest FarmBot status payload
- Home Assistant diagnostics download with the access token redacted

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

## Actions

### Execute a sequence

Use `farmbot.execute_sequence` with the numeric sequence ID from FarmBot:

```yaml
action: farmbot.execute_sequence
data:
  sequence_id: 12345
```

When more than one FarmBot integration is configured, also select the target FarmBot in the visual action editor or provide its `config_entry_id`.

### Move to an absolute coordinate

Use `farmbot.move_to` with X, Y and Z coordinates in millimetres. Speed is optional and defaults to 100 percent:

```yaml
action: farmbot.move_to
data:
  x: 1000
  y: 500
  z: 0
  speed: 100
```

## FarmBot power schedule example

FarmBot cannot switch its own upstream power back on after shutdown, so power scheduling should be handled by a Home Assistant-controlled smart plug or relay.

Replace `switch.farmbot_power` with the entity controlling power to your FarmBot:

```yaml
alias: FarmBot power schedule
description: Power FarmBot on at 8:00 AM and off at 6:00 PM every day
triggers:
  - trigger: time
    at: "08:00:00"
    id: power_on
  - trigger: time
    at: "18:00:00"
    id: power_off
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: power_on
        sequence:
          - action: switch.turn_on
            target:
              entity_id: switch.farmbot_power
      - conditions:
          - condition: trigger
            id: power_off
        sequence:
          - action: switch.turn_off
            target:
              entity_id: switch.farmbot_power
mode: single
```

## Manual installation

Manual installation remains available for development and recovery. Copy `custom_components/farmbot` into the Home Assistant `config/custom_components` directory, restart Home Assistant, then add **FarmBot** through **Settings → Devices & services → Add integration**.

## Project status

Version `0.3.3` adds the `farmbot.execute_sequence` and `farmbot.move_to` Home Assistant actions while retaining the existing authentication, MQTT, entity and diagnostics features.

This project is community-maintained and is not an official FarmBot or Home Assistant integration.
