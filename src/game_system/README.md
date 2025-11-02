# Game System Architecture

A state-machine-based interactive game system for Raspberry Pi with LED strips and button controls.

## Architecture Overview

### Core Components

- **GameState**: Abstract base class for game modes (Idle, Amplify, Party, etc.)
- **Animation**: Time-based animations with configurable speed and rendering
- **SequenceDetector**: Detects button press sequences for complex transitions
- **GameController**: Main orchestrator handling state transitions and timing

### Directory Structure

```
src/game_system/
├── __init__.py              # Public API exports
├── base_classes.py          # GameState and Animation abstract classes
├── sequence_detector.py     # Button sequence detection
├── game_controller.py       # Main game controller
├── states.py                # Concrete state implementations
├── animations.py            # Concrete animation implementations
└── README.md               # This file
```

## Usage Example

```python
from game_system import GameController, IdleState
from button_system import ButtonReader
from led_system import PixelStripAdapter

# Setup hardware
button_reader = ButtonReader(button_pins=[22, 23, 24, ...])
led_strips = [PixelStripAdapter(...), PixelStripAdapter(...)]

# Create game controller
game = GameController(button_reader, led_strips, target_fps=30)

# Run game loop
game.run_with_frame_limiting()
```

## Implemented States

### IdleState
- **Animation**: Dim blue breathing effect
- **Transitions**: Any button press → AmplifyState

### AmplifyState  
- **Animation**: Rainbow cycle for each pressed button (30 LEDs per button)
- **Transitions**: 
  - No buttons pressed → IdleState
  - All buttons pressed → PartyState (when implemented)

### TestState
- **Animation**: Static red/green split for testing
- **Transitions**: Any button press → IdleState

## Global Sequences

- **Code Mode**: Button 7 pressed 3 times (1.5s timeout) → TestState

## Creating New States

1. **Inherit from GameState**:
```python
class MyState(GameState):
    def __init__(self):
        super().__init__()
        self.my_data = {}
        self.animations = [MyAnimation()]
    
    def handle_button_change(self, button_state):
        # Return new state or None
        
    def update(self, dt):
        # Update animations
        
    def render(self, led_strips):
        # Render to LEDs
```

2. **Add to states.py** and update `__init__.py`

## Creating New Animations

1. **Inherit from Animation**:
```python
class MyAnimation(Animation):
    def __init__(self, speed_ms=50):
        super().__init__(speed_ms, "MyAnimation")
        
    def advance(self, dt):
        # Update animation state
        
    def render(self, led_strips):
        # Render to LEDs
```

2. **Add to animations.py** and update `__init__.py`

## Performance Notes

- Target 30 FPS for RPi 3 with 600 LEDs total
- Each `strip.show()` takes ~10ms (budget accordingly)
- Use integer math in tight animation loops
- Reuse Pixel objects to minimize allocations

## Future Extensions

- Music system integration
- State persistence
- Network remote control
- Hardware failure recovery
- Performance monitoring dashboard
