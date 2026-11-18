# ecoNEXT

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant custom integration for Plum heat pump controllers via the [econext-gateway](https://github.com/LeeNuss/econext-gateway).

## Overview

This integration connects to an econext-gateway running on your local network, providing real-time monitoring and control of your GM3 protocol based heat pump controllers (ecoMAX360i).

## Features

- Temperature sensors (thermostat, calculated, room setpoint, DHW, outdoor)
- Climate entities for heating circuits with comfort/eco presets
- Number entities for editable parameters (setpoints, hysteresis, heating curves)
- Select entities for operating modes and circuit types
- Switch entities for enabling/disabling functions
- Binary sensors for alarm states
- Button entities for heat pump commands
- Virtual thermostat emulation (use HA temperature sensors as heat pump input)
- Dew-safe UFH cooling controller (beta) — drives a fan-coil circuit's cooling cycle with condensation protection, using your dew-point sensor

## Requirements

- Home Assistant 2024.1.0 or newer
- A running [econext-gateway](https://github.com/LeeNuss/econext-gateway) instance connected to your controller via RS-485

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** > three-dot menu > **Custom repositories**
3. Add `https://github.com/LeeNuss/econext` as type **Integration**
4. Click **Download** and restart Home Assistant

### Manual

Copy the `custom_components/econext` folder to your Home Assistant `config/custom_components/` directory and restart.

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **ecoNEXT**
3. Enter the IP address and port (default: 8000) of your gateway

## Schedule Card

For weekly heating schedule management, install the [econext-schedule-card](https://github.com/LeeNuss/econext-schedule-card) Lovelace card:

1. Open HACS > **Frontend** > three-dot menu > **Custom repositories**
2. Add `https://github.com/LeeNuss/econext-schedule-card` as type **Dashboard**
3. Click **Download** and reload your browser

## Virtual Thermostat

The virtual thermostat lets you use any Home Assistant temperature sensor as the room temperature input for your heat pump. This is ideal if you have multiple temperature sensors and want to use a weighted average instead of the reading from a single physical thermostat.

### Prerequisites

Requires [econext-gateway](https://github.com/LeeNuss/econext-gateway) v0.2.0 or above. Thermostat support is enabled by default in the gateway from v0.2.0 onwards — no extra install flag needed. See the [gateway setup instructions](https://github.com/LeeNuss/econext-gateway#virtual-thermostat) for details.

### Setup

1. **Configure the temperature source:**
   Go to **Settings** > **Integrations** > **ecoNEXT** > gear icon.
   Select a temperature sensor entity (e.g. `sensor.weighted_room_temp`) under **Virtual thermostat temperature source**.
   The integration will submit this reading to the gateway every 10 seconds.

2. **Pair the virtual thermostat:**
   A new **Virtual Thermostat** device appears under the integration. Press the **Pair** button in HA — this opens a 60-second pairing window on the gateway.

3. **Run the panel pairing wizard:**
   Within those 60 seconds, on the Grant Aerona Smart Controller:

   - From the main menu, tap the **current temperature** of the circuit you want this thermostat assigned to.
   - On the screen that opens, tap the **thermostat-with-plus** icon in the bottom-left corner — the pairing wizard starts.

   (Alternative path: **System settings -> Circuit settings -> [target circuit] -> Thermostat**, confirming overwrite if a thermostat is already paired.)

   Tap `>` on the panel to accept once the wizard detects the thermostat.

   The **State** entity in HA will move from "Pairing requested" to "Paired (addr NNN)" once the panel assigns an address.

### Virtual Thermostat Device

After configuration, the device shows:

| Entity                   | Description                                                                                                                                                                                                                                                                                           |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Reported temperature** | The temperature the heat pump sees (with history graph)                                                                                                                                                                                                                                               |
| **State**                | Connection state. Possible values: `Unpaired` (not yet paired), `Pairing requested` (60s pairing window open), `Paired (addr NNN)` (live and serving the panel), `Stale` (paired but no temperature updates received within the last 5 minutes — gateway has fallen back to a fixed value on the bus) |
| **Source sensor**        | Which HA entity feeds the temperature (diagnostic)                                                                                                                                                                                                                                                    |
| **Pair**                 | Button to trigger bus pairing (icon changes based on state)                                                                                                                                                                                                                                           |

### Notes

- The virtual thermostat coexists alongside a real ecoSTER thermostat on separate circuits
- The last submitted temperature is persisted to disk and survives gateway restarts
- If the source sensor becomes unavailable, the last known temperature is kept
- To re-pair at a new address, press the Pair button again
- To disable, clear the temperature source in the integration settings

### Troubleshooting

- **State stuck on "Pairing requested"** — the panel was not in pairing mode within the 60s window. Re-press the Pair button after putting the panel into pairing mode.
- **State shows "Stale"** — the configured source sensor stopped publishing updates. Check the source entity in HA; the gateway falls back to a fixed bus temperature (19 C by default) until updates resume.
- **No Virtual Thermostat device appears** — verify the gateway is reachable and `GET http://<gateway>:8000/api/thermostat/status` returns `"enabled": true`. If `enabled` is false, the gateway was installed before thermostat support was on by default — re-run the gateway installer or set `ECONEXT_THERMOSTAT_ENABLED=true` and restart it.

## Cooling Controller (beta)

A dew-safe UFH cooling controller built into the integration. When there is
cooling demand on the selected circuit, it drives the heat pump's
cooling-water target through a small state machine that "dips" the target
low to force the HP to start, holds a dew-safe working target while running,
and force-stops before the loop flow falls far enough below room dew point
to risk condensation on the pipes. It adds the dew-point protection the HP
firmware does not have.

The controller is **off by default**. It only does anything once you enable
it and pick a dew-point sensor in the integration's options.

### Prerequisites

- A dew-point sensor for the cooled rooms — **required**. Without it there
  is no dew safety and the controller refuses to cool. Any sensor that
  reports a dew temperature works (e.g. a
  [thermal_comfort](https://github.com/dolezsa/thermal_comfort) max-dew-point
  sensor across the cooled rooms).
- An OEM/manifold flow-temperature sensor — **optional**. If provided it is
  used in preference to the heat pump's internal flow reading for dew
  safety; if absent the integration falls back to the HP flow temperature.
- The circuit you want to cool must be a circuit the cooling controller
  supports (1–3).

### Setup

1. Go to **Settings** > **Devices & Services** > **ecoNEXT** > **Configure**.
2. Set **Enable cooling controller** on.
3. Pick the **Dew point sensor** (required) and, if you have one, the
   **OEM/manifold flow temperature**.
4. Choose the **Cooling circuit** (1–3, default 2).
5. Save. The integration reloads and a new **Cooling (econext)** device
   appears.

On first save the integration will switch teh selected circuit to "fan coil", as
this is the only mode it can reach temperature below 18 degrees
(needed for the initial dip to start the cooling cycle).

### Cooling (econext) device

The new device exposes:

- **Switches** — `Cooling enable`, `Cooling dry run` (no real writes; observe and log only).
- **Sensors** — `Cooling cycle state` (idle/starting/running/cooldown),
  `Cooling safe target`, `Cooling working target`, `Flow below dew point`,
  `Last cooling run`, `Last cooling cycle end`.
- **Binary sensors** — `HP quiet`, `Cooling schedule active`.
- **Number tunables** — production-tuned defaults are loaded on first run
  (working-target offset, soft / hard / panic floors and durations,
  break/timeout/max-run minutes, dip / cooldown targets, etc.). Each is a
  RestoreNumber so adjustments survive restarts.

### Recommended first-run

Leave **Cooling dry run** on for a day. Watch
`sensor.cooling_econext_cooling_cycle_state` and `Flow below dew point`
across a real demand period — every decision is also logged

### Notes & limitations (beta)

- The cooling target is hard-floored at **16 °C** — the dip-to-start can't
  command the HP below that, to preserve dew margin on high-dew days.
- On dew-sensor outage the controller skips starting and, if running, winds
  the current cycle down.
- Integration sets min pump-speed to 85% to reduce the deltaT, allowing the cooling to run for longer before
  dew point is reached. Resets to previous value when HP work mode changes back to heating.
- The cooling feature is gated entirely behind the **Enable cooling
  controller** option — turn it off and no cooling entities, writes or
  bookkeeping happen.
- Beta caveat: this is a new feature, please open a new issue and share logs if you run into any poblems.

## Supported Devices

- ecoMAX360i controllers
