"""
Concrete game state implementations
"""

from typing import List, Set, Dict, Optional, TYPE_CHECKING

from .base_classes import GameState
from .animations import BreathingAnimation, RainbowAnimation, StaticColorAnimation

if TYPE_CHECKING:
    from button_system.button_state import ButtonState
    from led_system.interfaces import LedStrip
    from led_system.pixel import Pixel
    from .base_classes import Animation


class IdleState(GameState):
    """
    Idle game state - dim breathing animation, waiting for button input.
    
    Transitions:
    - Any button press → AmplifyState
    - Button sequence (handled by GameController) → other states
    """
    
    def __init__(self):
        super().__init__()
        
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # Create dim blue breathing animation
        dim_blue = Pixel(0, 50, 100)  # Dim blue color
        self.breathing_animation = BreathingAnimation(
            color=dim_blue,
            speed_ms=100,
            brightness_range=(0.1, 0.6)
        )
        
        self.animations: List['Animation'] = [self.breathing_animation]
    
    def handle_button_change(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Handle button changes in idle state"""
        # Transition to Amplify if any button is pressed
        if button_state.total_buttons_pressed > 0:
            pressed_buttons = {i for i, pressed in enumerate(button_state.for_button) if pressed}
            return AmplifyState(pressed_buttons=pressed_buttons)
        
        return None
    
    def update(self, dt: float) -> None:
        """Update idle state animations"""
        for animation in self.animations:
            animation.update(dt)
    
    def render(self, led_strips: List['LedStrip']) -> None:
        """Render idle state to LED strips"""
        # Clear strips first
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for strip in led_strips:
            strip[:] = black
        
        # Render animations
        for animation in self.animations:
            animation.render(led_strips)


class AmplifyState(GameState):
    """
    Amplify state - rainbow animations for each pressed button.
    
    Each button controls a 30-LED section with its own rainbow animation.
    Dynamically adds/removes animations based on button presses.
    
    Transitions:
    - No buttons pressed → IdleState  
    - All buttons pressed → PartyState (if implemented)
    """
    
    LEDS_PER_BUTTON = 30
    
    def __init__(self, pressed_buttons: Set[int] = None):
        super().__init__()
        self.pressed_buttons: Set[int] = pressed_buttons or set()
        self.button_animations: Dict[int, RainbowAnimation] = {}
        self._setup_animations()
    
    def _setup_animations(self):
        """Create rainbow animations for currently pressed buttons"""
        for button_id in self.pressed_buttons:
            self._create_button_animation(button_id)
    
    def _create_button_animation(self, button_id: int):
        """Create rainbow animation for specific button"""
        start_led = button_id * self.LEDS_PER_BUTTON
        end_led = start_led + self.LEDS_PER_BUTTON
        
        self.button_animations[button_id] = RainbowAnimation(
            led_range=(start_led, end_led),
            speed_ms=50,
            hue_shift_per_frame=8
        )
    
    def handle_button_change(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Handle button changes in amplify state"""
        new_pressed = {i for i, pressed in enumerate(button_state.for_button) if pressed}
        
        # Return to Idle if no buttons pressed
        if not new_pressed:
            return IdleState()
        
        # Check for all buttons pressed (Party mode - if you implement it later)
        # if len(new_pressed) == 10:  # Assuming 10 total buttons
        #     return PartyState()
        
        # Update button animations for changed buttons
        self._update_button_animations(new_pressed)
        
        return None
    
    def _update_button_animations(self, new_pressed: Set[int]):
        """Update animations based on newly pressed/released buttons"""
        # Remove animations for released buttons
        for button_id in list(self.button_animations.keys()):
            if button_id not in new_pressed:
                del self.button_animations[button_id]
        
        # Add animations for newly pressed buttons
        for button_id in new_pressed:
            if button_id not in self.button_animations:
                self._create_button_animation(button_id)
        
        self.pressed_buttons = new_pressed
    
    def update(self, dt: float) -> None:
        """Update amplify state animations"""
        for animation in self.button_animations.values():
            animation.update(dt)
    
    def render(self, led_strips: List['LedStrip']) -> None:
        """Render amplify state to LED strips"""
        # Clear strips first
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for strip in led_strips:
            strip[:] = black
        
        # Render each button's animation
        for animation in self.button_animations.values():
            animation.render(led_strips)


class TestState(GameState):
    """
    Simple test state for development and debugging.
    
    Shows static colors to verify LED functionality.
    """
    
    def __init__(self):
        super().__init__()
        
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # Create test animations
        red = Pixel(255, 0, 0)
        green = Pixel(0, 255, 0)
        
        self.animations: List['Animation'] = [
            StaticColorAnimation(red, led_range=(0, 150)),    # First half red
            StaticColorAnimation(green, led_range=(150, 300)) # Second half green
        ]
    
    def handle_button_change(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Handle button changes in test state"""
        # Return to idle on any button press
        if button_state.any_changed and button_state.total_buttons_pressed > 0:
            return IdleState()
        
        return None
    
    def update(self, dt: float) -> None:
        """Update test state animations"""
        for animation in self.animations:
            animation.update(dt)
    
    def render(self, led_strips: List['LedStrip']) -> None:
        """Render test state to LED strips"""
        for animation in self.animations:
            animation.render(led_strips)
