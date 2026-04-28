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

## Supported Devices

- Plum ecoMAX controllers (ecoMAX360i and similar)
- ecoTRONIC heat pump controllers
- Other devices using the GM3 serial protocol
