## UFH Flow Temperature Calculation

### Overview

The Grant Aerona Smart Controller calculates the target flow temperature for underfloor heating based on several factors. When **Pump Blockade is OFF**, the controller handles this internally. When **Pump Blockade is ON**, the controller only provides a base temperature and we must apply the room correction logic ourselves.

---

### Inputs

| Parameter | Description |
|-----------|-------------|
| **Base curve temperature** | Calculated from heating curve + shift based on outdoor temperature |
| **Room temperature** | Current measured room temperature |
| **Room setpoint** | Target room temperature |
| **Decrease water temperature** | Reduction applied when room is at target (default: 6°C) |
| **Room temperature correction** | Multiplier for temperature difference (default: 6) |
| **Hysteresis** | Dead band around setpoint (default: 0.3°C) |

---

### Calculation Logic (Pump Blockade ON)
```
diff = setpoint − room_temp
```

| Condition | Description | Formula |
|-----------|-------------|---------|
| `diff > hysteresis` | Room is cold, needs heating | `base + (diff − hysteresis) × correction` |
| `0 ≤ diff ≤ hysteresis` | Room slightly below setpoint | `base − decrease` |
| `-hysteresis < diff < 0` | Room slightly above setpoint | `base − (|diff| + hysteresis) × correction` |
| `diff ≤ -hysteresis` | Room is warm, reduce heating | `base − decrease − |diff| × correction` |

---

### Example Calculations

Settings: base = 31.9°C, decrease = 6°C, correction = 6, hysteresis = 0.3°C

| Setpoint | Room | Diff | Condition | Calculation | Result |
|----------|------|------|-----------|-------------|--------|
| 21.0 | 19.3 | +1.7 | Cold | 31.9 + (1.7 − 0.3) × 6 | 40.3°C |
| 19.5 | 19.3 | +0.2 | Slightly cold | 31.9 − 6 | 25.9°C |
| 19.5 | 19.5 | 0.0 | At setpoint | 31.9 − 6 | 25.9°C |
| 19.5 | 19.6 | −0.1 | Slightly warm | 31.9 − (0.1 + 0.3) × 6 | 29.5°C |
| 19.0 | 19.3 | −0.3 | Warm | 31.9 − 6 − 0.3 × 6 | 24.1°C |

---

### Summary

- **Room too cold**: Flow temperature increases aggressively above base
- **Room near setpoint**: Flow temperature drops by the "decrease water temperature" value to maintain without overshooting
- **Room too warm**: Flow temperature reduces further to prevent overheating
