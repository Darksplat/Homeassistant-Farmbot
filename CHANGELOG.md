# Changelog

All notable changes to the Home Assistant FarmBot integration are documented here.

## v0.3.3 — 16 July 2026

### Added

- Added the `farmbot.execute_sequence` Home Assistant action for running an existing FarmBot sequence by sequence ID.
- Added the `farmbot.move_to` Home Assistant action for moving FarmBot to absolute X, Y and Z coordinates.
- Added an optional movement speed field for `farmbot.move_to`, constrained to 1–100 percent.
- Added config-entry selection so actions can target the correct FarmBot when more than one FarmBot integration is configured.
- Added `services.yaml` definitions so both actions appear correctly in Home Assistant's visual automation and script editors.
- Added README documentation and YAML examples for both actions.

### Usage

Run an existing FarmBot sequence:

```yaml
action: farmbot.execute_sequence
data:
  sequence_id: 12345
```

Move FarmBot to an absolute coordinate:

```yaml
action: farmbot.move_to
data:
  x: 1000
  y: 500
  z: 0
  speed: 100
```

When multiple FarmBot integrations are configured, select the appropriate FarmBot config entry in the visual editor or supply its config entry ID in the action data.

### Upgrade notes

- Restart Home Assistant after updating the integration.
- Existing entities and configuration entries are retained.
- No configuration migration is required.
- FarmBot must be connected to MQTT before either action can run.

### Technical notes

The integration already contained the underlying MQTT RPC implementations for sequence execution and absolute movement. Version 0.3.3 exposes those commands as registered Home Assistant actions with validation and visual-editor metadata.
