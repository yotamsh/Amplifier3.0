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
    from .game_controller import GameController


class IdleState(GameState):
    """
    Idle game state - dim breathing animation, waiting for button input.
    
    Transitions:
    - Any button press → AmplifyState
    - Button sequence (handled by GameController) → other states
    """
    
    def __init__(self):
        super().__init__()
        self.game_controller: Optional['GameController'] = None
        
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
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update idle state - handle buttons, animations, and LED rendering"""
        # Check for state transitions
        if button_state.total_buttons_pressed > 0:
            pressed_buttons = {i for i, pressed in enumerate(button_state.for_button) if pressed}
            new_state = AmplifyState(pressed_buttons=pressed_buttons)
            return new_state
        
        # Update animations
        for animation in self.animations:
            animation.update(0)  # dt not needed for time-based animations
        
        # Render to LED strips
        if self.game_controller:
            # Clear strips first
            from led_system.pixel import Pixel
            black = Pixel(0, 0, 0)
            for strip in self.game_controller.led_strips:
                strip[:] = black
            
            # Render animations
            for animation in self.animations:
                animation.render(self.game_controller.led_strips)
        
        return None


class AmplifyState(GameState):
    """
    Amplify state - rainbow animations for each pressed button.
    
    Each button controls an LED section with its own rainbow animation.
    Dynamically adds/removes animations based on button presses.
    
    Transitions:
    - No buttons pressed → IdleState  
    - All buttons pressed → PartyState (if implemented)
    """
    
    def __init__(self, pressed_buttons: Set[int] = None):
        super().__init__()
        self.game_controller: Optional['GameController'] = None
        self.pressed_buttons: Set[int] = pressed_buttons or set()
        self.button_animations: Dict[int, RainbowAnimation] = {}
    
    def on_enter(self) -> None:
        """Called when entering this state - setup animations with proper game_controller"""
        self._setup_animations()
    
    def _setup_animations(self):
        """Create rainbow animations for currently pressed buttons"""
        for button_id in self.pressed_buttons:
            self._create_button_animation(button_id)
    
    def _create_button_animation(self, button_id: int):
        """Create rainbow animation for specific button"""
        # Calculate LED distribution
        leds_per_button = 30  # Fallback
        if self.game_controller:
            total_leds = sum(strip.num_pixels() for strip in self.game_controller.led_strips)
            button_count = self.game_controller.button_reader.get_button_count()
            leds_per_button = total_leds // button_count
            
        start_led = button_id * leds_per_button
        end_led = start_led + leds_per_button
        
        self.button_animations[button_id] = RainbowAnimation(
            led_range=(start_led, end_led),
            speed_ms=50,
            hue_shift_per_frame=8
        )
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update amplify state - handle buttons, animations, and LED rendering"""
        new_pressed = {i for i, pressed in enumerate(button_state.for_button) if pressed}
        
        # Check for state transitions
        if not new_pressed:
            return IdleState()
        
        # Update button animations for changed buttons
        self._update_button_animations(new_pressed)
        
        # Update animations
        for animation in self.button_animations.values():
            animation.update(0)  # dt not needed for time-based animations
        
        # Render to LED strips
        if self.game_controller:
            # Clear strips first
            from led_system.pixel import Pixel
            black = Pixel(0, 0, 0)
            for strip in self.game_controller.led_strips:
                strip[:] = black
            
            # Render each button's animation
            for animation in self.button_animations.values():
                animation.render(self.game_controller.led_strips)
        
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


class TestState(GameState):
    """
    Simple test state for development and debugging.
    
    Shows static colors to verify LED functionality.
    """
    
    def __init__(self):
        super().__init__()
        self.game_controller: Optional['GameController'] = None
        
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # Create test animations
        red = Pixel(255, 0, 0)
        green = Pixel(0, 255, 0)
        
        self.animations: List['Animation'] = [
            StaticColorAnimation(red, led_range=(0, 150)),    # First half red
            StaticColorAnimation(green, led_range=(150, 300)) # Second half green
        ]
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update test state - handle buttons, animations, and LED rendering"""
        # Check for state transitions
        if button_state.any_changed and button_state.total_buttons_pressed > 0:
            return IdleState()
        
        # Update animations
        for animation in self.animations:
            animation.update(0)  # dt not needed for time-based animations
        
        # Render to LED strips
        if self.game_controller:
            for animation in self.animations:
                animation.render(self.game_controller.led_strips)
        
        return None
