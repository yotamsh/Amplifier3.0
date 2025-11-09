"""
Game state base class and concrete implementations
"""

from abc import ABC, abstractmethod
from typing import List, Set, Dict, Optional, TYPE_CHECKING

from game_system.animations import BreathingAnimation, RainbowAnimation, StaticColorAnimation, AmplifyAnimation, AnimationDelayWrapper, IdleAnimation

if TYPE_CHECKING:
    from button_system.button_state import ButtonState
    from led_system.interfaces import LedStrip
    from game_system.animations import Animation
    from game_system.game_manager import GameManager
else:
    from led_system.pixel import Pixel


class GameState(ABC):
    """
    Abstract base class for all game states.
    
    Each state represents a distinct game mode with its own:
    - Button handling logic
    - Animation management 
    - State transition conditions
    """
    
    def __init__(self, game_manager: 'GameManager'):
        """Initialize the game state"""
        self.game_manager: 'GameManager' = game_manager
    
    @abstractmethod
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """
        Update state logic, handle button changes, update animations, and render LEDs.
        
        Args:
            button_state: Current button state with edge detection
            
        Returns:
            New GameState instance if transition needed, None to stay in current state
        """
        pass
    
    def on_enter(self) -> None:
        """Called when entering this state - logs state name and calls custom enter"""
        self.game_manager.logger.info(f"Entering state: {self.__class__.__name__}")
        self.custom_on_enter()
    
    def on_exit(self) -> None:
        """Called when exiting this state - logs state name and calls custom exit"""
        self.game_manager.logger.info(f"Exiting state: {self.__class__.__name__}")
        self.custom_on_exit()
    
    @abstractmethod
    def custom_on_enter(self) -> None:
        """Custom enter logic (override in subclasses)"""
        pass
    
    @abstractmethod
    def custom_on_exit(self) -> None:
        """Custom exit logic (override in subclasses)"""
        pass


class IdleState(GameState):
    """
    Idle game state - dim breathing animation, waiting for button input.
    
    Transitions:
    - Any button press → AmplifyState
    - Button sequence (handled by GameController) → other states
    """
    
    def __init__(self, game_controller: 'GameController'):
        super().__init__(game_controller)
        self.animations: List['Animation'] = []
    
    def custom_on_enter(self) -> None:
        """Called when entering idle state - setup delayed scanner animations"""
        # Create bouncing rainbow scanner animation for each strip, wrapped with 2-second delay
        self.animations = []
        
        for strip in self.game_manager.led_strips:
            # Create the idle scanner animation
            idle_anim = IdleAnimation(
                strip=strip,
                speed_ms=50,      # Very fast scanner movement
                hue_increment=3,  # Rainbow cycling speed 
                fade_amount=20    # Trail fading strength
            )
            
            # Wrap it with a 2-second delay
            delayed_idle = AnimationDelayWrapper(
                target_animation=idle_anim,
                delay_ms=2000  # 2 seconds of darkness
            )
            
            self.animations.append(delayed_idle)
    
    def custom_on_exit(self) -> None:
        """Called when exiting idle state - cleanup if needed"""
        pass
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update idle state - handle buttons, animations, and LED rendering"""
        # Check for state transitions - any button pressed goes to Amplify
        if button_state.total_buttons_pressed > 0:
            return AmplifyState(self.game_manager, button_state.for_button)
        
        # Update animations (they handle their own rendering and timing)
        for animation in self.animations:
            animation.update_if_needed()
        
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
    
    def __init__(self, game_manager: 'GameManager', pressed_buttons: List[bool] = None):
        super().__init__(game_manager)
        # Create class logger for this state
        self.logger = game_manager.logger.create_class_logger("AmplifyState")
        
        # Initialize pressed buttons state (list of bools, same as ButtonState.for_button)
        button_count = game_manager.button_reader.get_button_count()
        self.pressed_buttons: List[bool] = pressed_buttons or [False] * button_count
        
        # Initialize animations list with an amplify animation on strip 1 (index 0)
        self.animations: List['Animation'] = []
        first_strip = game_manager.led_strips[0]
        self.amplify_anim = AmplifyAnimation(
            strip=first_strip,
            button_count=game_manager.button_reader.get_button_count(),
            speed_ms=50,
            hue_shift_per_frame=12
        )
        self.animations.append(self.amplify_anim)
        
        # Initialize the animation with the current button state
        self.amplify_anim.set_pressed_buttons(self.pressed_buttons)
        
        # Print pressed button indexes on init
        pressed_indexes = [i for i, pressed in enumerate(self.pressed_buttons) if pressed]
        if pressed_indexes:
            self.logger.debug(f"AmplifyState initialized with buttons: {pressed_indexes}")
        else:
            self.logger.debug("AmplifyState initialized with no buttons pressed")
    
    def custom_on_enter(self) -> None:
        """Called when entering this state - no setup needed"""
        pass
    
    def custom_on_exit(self) -> None:
        """Called when exiting this state - cleanup if needed"""
        pass
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update amplify state - handle buttons, animations, and LED rendering"""
        # Check for state transitions first - no buttons pressed goes back to Idle
        if button_state.total_buttons_pressed == 0:
            return IdleState(self.game_manager)
        
        # Update pressed buttons state to current button state
        self.pressed_buttons = button_state.for_button.copy()
        
        # Update the amplify animation with current button state
        self.amplify_anim.set_pressed_buttons(self.pressed_buttons)
        
        # Print pressed button indexes on update
        if button_state.any_changed:
            pressed_indexes = [i for i, pressed in enumerate(button_state.for_button) if pressed]
            self.logger.debug(f"AmplifyState button change - currently pressed: {pressed_indexes}")
        
        # Update animations (they handle their own rendering and timing)
        for animation in self.animations:
            animation.update_if_needed()
        
        return None
    


class TestState(GameState):
    """
    Simple test state for development and debugging.
    
    Shows static colors to verify LED functionality.
    """
    
    def __init__(self, game_controller: 'GameController'):
        super().__init__(game_controller)
        self.animations: List['Animation'] = []
    
    def custom_on_enter(self) -> None:
        """Called when entering test state - setup static color animations"""
        # Create test animations for each strip
        red = Pixel(255, 0, 0)
        green = Pixel(0, 255, 0)
        
        self.animations = []
        for i, strip in enumerate(self.game_manager.led_strips):
            if i == 0:
                # First strip: red color
                red_anim = StaticColorAnimation(strip, red)
                self.animations.append(red_anim)
            else:
                # Other strips: green color
                green_anim = StaticColorAnimation(strip, green)
                self.animations.append(green_anim)
    
    def custom_on_exit(self) -> None:
        """Called when exiting test state - cleanup if needed"""
        pass
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update test state - handle buttons, animations, and LED rendering"""
        # Check for state transitions
        if button_state.any_changed and button_state.total_buttons_pressed > 0:
            return IdleState(self.game_manager)
        
        # Update animations (they handle their own rendering and timing)
        for animation in self.animations:
            animation.update_if_needed()
        
        return None
