# Keyboard Debug Mode - Usage Guide

## Overview

The amplifier now supports **keyboard input over SSH** for debugging button presses without physical buttons!

## How It Works

- **Toggle Mode**: Press digit key `0-9` to toggle that button ON/OFF
- **OR Logic**: Button activates if GPIO is HIGH **OR** keyboard toggle is ON
- **Works over SSH**: Uses stdin (non-blocking), no special libraries needed
- **Zero dependencies**: Uses standard Python `select` module

## Usage

### Current Setup (amplifier.py)

The system is currently configured with `GPIOWithKeyboardSampler`:

```python
button_sampler = GPIOWithKeyboardSampler(
    button_pins=config.button_config.pins,
    pull_mode=config.button_config.pull_mode,
    logger=button_reader_logger
)
```

### Keyboard Controls

When running the amplifier:
- Press `0` - Toggle button 0 ON/OFF
- Press `1` - Toggle button 1 ON/OFF
- Press `2` - Toggle button 2 ON/OFF
- Press `3` - Toggle button 3 ON/OFF
- etc.

Each keypress toggles the button state. The logs will show:
```
🎮 Keyboard debug enabled: Press digit keys 0-9 to toggle buttons (works over SSH)
Keyboard: Button 0 toggled ON (key '0')
Keyboard: Button 0 toggled OFF (key '0')
```

### Switching to Production Mode

For production (no keyboard debug), simply change the sampler:

```python
# Debug mode (keyboard + GPIO)
button_sampler = GPIOWithKeyboardSampler(...)

# Production mode (GPIO only)
button_sampler = GPIOSampler(...)
```

## Architecture

### Clean Separation via Interfaces

```
IButtonSampler (interface)
├── GPIOSampler (production)
│   └── Pure GPIO reading
└── GPIOWithKeyboardSampler (debug)
    ├── Uses GPIOSampler internally
    └── Adds keyboard toggle layer
```

### Benefits

✅ **No test code in production** - Use `GPIOSampler` for production  
✅ **Debug over SSH** - No physical buttons needed for testing  
✅ **Toggle mode** - Simulates buttons being held down  
✅ **Clean architecture** - SOLID principles, dependency injection  
✅ **Easy switching** - Change one line to enable/disable debug  

## Button Mapping (Current Config)

```
Button 0 → GPIO 6  → Keyboard '0'
Button 1 → GPIO 5  → Keyboard '1'
Button 2 → GPIO 17 → Keyboard '2'
Button 3 → GPIO 22 → Keyboard '3'
```

## Example Session

```bash
ssh pi@raspberrypi
cd Amp3
source venv/bin/activate
python src/amplifier.py

# Press keyboard keys:
0   # Toggle button 0 ON
1   # Toggle button 1 ON
0   # Toggle button 0 OFF (was ON, now OFF)
2   # Toggle button 2 ON
```

## Technical Details

- **Non-blocking**: Uses `select.select()` with 0 timeout
- **No terminal mode changes**: Works in normal terminal
- **Thread-safe**: Single-threaded, no race conditions
- **Graceful fallback**: If stdin unavailable, logs warning and continues with GPIO-only


