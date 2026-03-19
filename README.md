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

Requires [econext-gateway](https://github.com/LeeNuss/econext-gateway) v0.2.0 or above, installed with thermostat support enabled. See the [gateway setup instructions](https://github.com/LeeNuss/econext-gateway#virtual-thermostat) for details.

### Setup

1. **Configure the temperature source:**
   Go to **Settings** > **Integrations** > **ecoNEXT** > gear icon.
   Select a temperature sensor entity (e.g. `sensor.weighted_room_temp`) under **Virtual thermostat temperature source**.
   The integration will submit this reading to the gateway every 10 seconds.

2. **Pair the virtual thermostat:**
   A new **Virtual Thermostat** device appears under the integration. Press the **Pair** button,
   then enter **pairing mode** on the panel within 60 seconds.

3. **Assign to a circuit:**
   On the panel, assign the new thermostat to the desired heating circuit.

### Virtual Thermostat Device

After configuration, the device shows:

| Entity | Description |
|--------|-------------|
| **Reported temperature** | The temperature the heat pump sees (with history graph) |
| **State** | Connection state: "Paired (addr 164)" / "Pairing requested" / "Unpaired" / "Stale" |
| **Source sensor** | Which HA entity feeds the temperature (diagnostic) |
| **Pair** | Button to trigger bus pairing (icon changes based on state) |

### Notes

- The virtual thermostat coexists alongside a real ecoSTER thermostat on separate circuits
- The last submitted temperature is persisted to disk and survives gateway restarts
- If the source sensor becomes unavailable, the last known temperature is kept
- To re-pair at a new address, press the Pair button again
- To disable, clear the temperature source in the integration settings

## Supported Devices

- Plum ecoMAX controllers (ecoMAX360i and similar)
- ecoTRONIC heat pump controllers
- Other devices using the GM3 serial protocol
