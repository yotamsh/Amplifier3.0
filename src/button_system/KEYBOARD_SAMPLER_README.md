# KeyboardSampler - GPIO-Free Testing

Pure keyboard-based button sampler for testing without Raspberry Pi GPIO hardware.

## Overview

`KeyboardSampler` provides a drop-in replacement for `GPIOSampler` that works entirely with keyboard input. Perfect for:

- 🖥️ Development on Mac/Linux without Raspberry Pi
- 🧪 Testing button logic without hardware
- 🐛 Debugging over SSH
- 🔄 CI/CD testing environments

## Features

✅ **No GPIO dependency** - Works on any system with Python  
✅ **Same interface** - Implements `IButtonSampler` just like GPIO versions  
✅ **Real-time input** - Uses raw terminal mode for instant response  
✅ **Toggle mode** - Press digit key once=ON, press again=OFF  
✅ **Built-in controls** - Space, reset, status display  

## Quick Start

### 1. Basic Usage

```python
from button_system import KeyboardSampler, ButtonReader
from utils.class_logger import ClassLogger

# Create logger
logger = ClassLogger("Test")

# Create keyboard sampler (10 virtual buttons)
sampler = KeyboardSampler(num_buttons=10, logger=logger)
sampler.setup()

# Use with ButtonReader
button_reader = ButtonReader(sampler=sampler, logger=logger)

# Read buttons
button_state = button_reader.read_buttons()
print(f"Pressed: {button_state.currently_pressed}")
```

### 2. Run Test Script

```bash
cd /Users/yotamsh/Downloads/personal/pRepos/Amp3
source venv_mac/bin/activate
python test_keyboard_sampler.py
```

## Controls

| Key | Action |
|-----|--------|
| `0-9` | Toggle virtual button ON/OFF |
| `Space` | Show current button states |
| `r` | Reset all buttons to OFF |
| `q` | Quit (in test mode) |

## Classes

### KeyboardSampler (Raw Mode)

Main implementation using raw terminal input for instant response.

**Pros:**
- Instant key response (no Enter needed)
- Works great over SSH
- Real-time button simulation

**Cons:**
- Requires TTY (terminal)
- Won't work with redirected stdin

```python
sampler = KeyboardSampler(
    num_buttons=10,  # Max 10 (digit keys 0-9)
    logger=logger
)
```

### KeyboardSamplerLineMode (Alternative)

Alternative implementation using line-buffered input.

**Pros:**
- Works without TTY
- Compatible with redirected input

**Cons:**
- Requires Enter after each key
- Less interactive

```python
sampler = KeyboardSamplerLineMode(
    num_buttons=10,
    logger=logger
)
```

## Comparison with GPIO Samplers

| Feature | KeyboardSampler | GPIOWithKeyboardSampler | GPIOSampler |
|---------|----------------|------------------------|-------------|
| GPIO hardware | ❌ No | ✅ Yes | ✅ Yes |
| Keyboard input | ✅ Yes | ✅ Yes | ❌ No |
| Raspberry Pi required | ❌ No | ✅ Yes | ✅ Yes |
| Works on Mac/Linux | ✅ Yes | ❌ No | ❌ No |
| Real GPIO reading | ❌ No | ✅ Yes | ✅ Yes |
| Best for | Testing/Dev | Debug on Pi | Production |

## Integration

### Replace GPIOSampler in Development

```python
# Production (on Raspberry Pi)
if ON_RASPBERRY_PI:
    sampler = GPIOSampler(
        button_pins=[22, 23, 24, 25, 26, 27, 28, 29, 30, 31],
        pull_mode=GPIO.PUD_OFF,
        logger=logger
    )
# Development (on Mac/Linux)
else:
    sampler = KeyboardSampler(
        num_buttons=10,
        logger=logger
    )

# Same interface for both!
button_reader = ButtonReader(sampler=sampler, logger=logger)
```

### Use in Main Amplifier System

Modify `src/amplifier.py` to conditionally use KeyboardSampler:

```python
import platform

def create_button_sampler(logger):
    """Create appropriate button sampler based on platform"""
    
    # Check if running on Raspberry Pi
    is_raspberry_pi = platform.machine().startswith('arm')
    
    if is_raspberry_pi:
        # Production: Use GPIO
        from button_system import GPIOSampler
        import RPi.GPIO as GPIO
        
        return GPIOSampler(
            button_pins=config.button_pins,
            pull_mode=GPIO.PUD_OFF,
            logger=logger
        )
    else:
        # Development: Use keyboard
        from button_system import KeyboardSampler
        
        return KeyboardSampler(
            num_buttons=len(config.button_pins),
            logger=logger
        )
```

## Limitations

- **Max 10 buttons** (limited by digit keys 0-9)
- **Requires TTY** for raw mode version
- **No simultaneous keys** - Terminal input is sequential

## Troubleshooting

### "Keyboard input not available"

**Problem:** Terminal is not interactive or stdin is redirected.

**Solutions:**
1. Run in an interactive terminal (not redirected)
2. Use SSH with TTY allocation: `ssh -t user@host`
3. Use `KeyboardSamplerLineMode` instead

### Terminal stays in raw mode after crash

**Problem:** Script crashed without cleanup, terminal doesn't echo input.

**Solution:**
```bash
# Reset terminal
reset

# Or restore settings manually
stty sane
```

### Keys not responding

**Problem:** Another process is reading stdin or terminal is in wrong mode.

**Solutions:**
1. Check no other process is using stdin
2. Restart terminal
3. Verify script has terminal access

## Example Output

```
======================================================================
🎮 Keyboard Sampler Test (NO GPIO Required)
======================================================================

This tests the button system using only keyboard input.
Perfect for development on Mac/Linux without Raspberry Pi!

CONTROLS:
  • Press digit keys 0-9 to toggle virtual buttons ON/OFF
  • Press SPACE to show current button states
  • Press 'r' to reset all buttons to OFF
  • Press 'q' to quit

======================================================================

🎮 Keyboard sampler initialized (NO GPIO)
   10 virtual buttons mapped to digit keys 0-9
   Press digit keys to toggle buttons ON/OFF
   Press 'q' to quit (in standalone mode)

🎮 Keyboard sampler ready! Start pressing digit keys...

🎮 Button 0 → ON (key '0')
🔵 Pressed: 0
⬆️  Rising edge: 0
🎮 Button 1 → ON (key '1')
🔵 Pressed: 0, 1
⬆️  Rising edge: 1
🎮 Button 0 → OFF (key '0')
🔵 Pressed: 1
⬇️  Falling edge: 0
```

## Files

- `keyboard_sampler.py` - Main implementation
- `test_keyboard_sampler.py` - Standalone test script
- `KEYBOARD_SAMPLER_README.md` - This file

## See Also

- `gpio_sampler.py` - Production GPIO sampler
- `gpio_keyboard_sampler.py` - GPIO + keyboard hybrid
- `interfaces.py` - IButtonSampler interface definition

