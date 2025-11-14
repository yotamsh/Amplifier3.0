"""
Game state base class and concrete implementations
"""

from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

from game_system.animations import AmplifyAnimation, AnimationDelayWrapper, IdleAnimation, PartyAnimation

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
        #self.game_manager.logger.debug(f"Entering state: {self.__class__.__name__}")
        self.custom_on_enter()
    
    def on_exit(self) -> None:
        """Called when exiting this state - logs state name and calls custom exit"""
        #self.game_manager.logger.debug(f"Exiting state: {self.__class__.__name__}")
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
    """
    
    def __init__(self, game_manager: 'GameManager'):
        super().__init__(game_manager)
        
        # Create bouncing rainbow scanner animation for each strip, wrapped with 2-second delay
        self.animations: List['Animation'] = []
        
        for strip in self.game_manager.led_strips:
            # Create the idle scanner animation
            idle_anim = IdleAnimation(
                strip=strip,
                speed_ms=30,      # Faster scanner movement (was 50)
                hue_increment=5,  # More hue change per frame (was 3)
                fade_amount=20    # Trail fading strength
            )
            
            # Wrap it with a 2-second delay
            delayed_idle = AnimationDelayWrapper(
                target_animation=idle_anim,
                delay_ms=2000  # 2 seconds of darkness
            )
            
            self.animations.append(delayed_idle)
    
    def custom_on_enter(self) -> None:
        """Actions when entering idle state"""
        # Load next random song to be ready for AmplifyState
        self.game_manager.sound_controller.load_next_song()
    
    def custom_on_exit(self) -> None:
        """Called when exiting idle state - cleanup if needed"""
        pass
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update idle state - handle buttons, animations, and LED rendering"""
        
        # Handle sequence timeout and pattern detection when all buttons released
        if button_state.total_buttons_pressed == 0:
            time_elapsed = self.game_manager.sequence_tracker.get_time_since_first_char()
            
            # Reset sequence if timed out (>2 seconds)
            if time_elapsed is not None and time_elapsed > 2.0:
                self.game_manager.sequence_tracker.reset()
            
        # Check for "111" pattern - enter code mode
        if self.game_manager.sequence_tracker.get_sequence() == "111":
            self.game_manager.logger.info("Triple 1 detected - entering code mode!")
            self.game_manager.sequence_tracker.reset()
            return CodeModeState(self.game_manager)
        
        # Check for state transitions - any button pressed goes to Amplify
        # ButtonReader handles ignore logic, so this is simple
        if button_state.total_buttons_pressed > 0:
            return AmplifyState(self.game_manager, button_state)
        
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
    """
    
    def __init__(self, game_manager: 'GameManager', button_state: 'ButtonState'):
        super().__init__(game_manager)
        
        # Create class logger for this state
        self.logger = game_manager.logger.create_class_logger("AmplifyState")
        
        # Set initial pressed buttons state
        self.pressed_buttons: List[bool] = button_state.for_button
        
        # Create amplify animation object on strip 1 (index 0)
        first_strip = game_manager.led_strips[0]
        self.amplify_anim = AmplifyAnimation(
            strip=first_strip,
            button_count=game_manager.button_reader.get_button_count(),
            speed_ms=100,  # Slower animation (100ms vs 50ms)
            hue_shift_per_frame=10  # Slower hue rotation
        )
        self.animations: List['Animation'] = [self.amplify_anim]
        
        # Store initial button state for custom_on_enter
        self.initial_button_state = button_state
    
    def custom_on_enter(self) -> None:
        """Actions when entering amplify state"""
        # Clear all LED strips from previous animations
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for strip in self.game_manager.led_strips:
            strip[:] = black
            strip.show()
        
        # Update animation with current button state
        self.amplify_anim.set_pressed_buttons(self.pressed_buttons)
        
        # Start music with initial volume
        self.game_manager.sound_controller.set_music_volume_by_buttons(
            self.initial_button_state.total_buttons_pressed
        )
        self.game_manager.sound_controller.start_loaded_song()
        
        # Debug logging
        pressed_indexes = [i for i, pressed in enumerate(self.pressed_buttons) if pressed]
        if pressed_indexes:
            self.logger.debug(f"AmplifyState activated with buttons: {pressed_indexes}")
        
    def custom_on_exit(self) -> None:
        """Called when exiting amplify state"""
        # Ignore any currently pressed buttons until they're released
        # This prevents immediately re-entering Amplify if buttons are still held
        self.game_manager.button_reader.ignore_pressed_until_released()
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update amplify state - handle buttons, animations, and LED rendering"""
        # Check for party mode - all buttons pressed
        button_count = self.game_manager.button_reader.get_button_count()
        if button_state.total_buttons_pressed == button_count:
            return PartyState(self.game_manager)
        
        # Check if song finished playing
        if not self.game_manager.sound_controller.is_song_playing():
            self.game_manager.sound_controller.stop_music()
            return IdleState(self.game_manager)
        
        # Check for state transitions - no buttons pressed goes back to Idle
        if button_state.total_buttons_pressed == 0:
            self.game_manager.sound_controller.stop_music()
            return IdleState(self.game_manager)
        
        # Update pressed buttons state to current button state
        self.pressed_buttons = button_state.for_button
        
        
        # Update if button state changed
        if button_state.any_changed:
            # Update the amplify animation and volume with current button state
            self.amplify_anim.set_pressed_buttons(self.pressed_buttons)
            self.game_manager.sound_controller.set_music_volume_by_buttons(button_state.total_buttons_pressed)
            pressed_indexes = [i for i, pressed in enumerate(button_state.for_button) if pressed]
            self.logger.debug(f"AmplifyState button change - currently pressed: {pressed_indexes}")
        
        # Update animations (they handle their own rendering and timing)
        for animation in self.animations:
            animation.update_if_needed()
        
        return None


class PartyState(GameState):
    """
    Party state - triggered when all buttons are pressed.
    
    Features:
    - Plays win sound
    - Sets music to maximum volume
    - Crazy multi-effect animation
    - Returns to idle when song ends
    
    Transitions:
    - Song finished → IdleState
    """
    
    def __init__(self, game_manager: 'GameManager'):
        super().__init__(game_manager)
        
        # Create logger
        self.logger = game_manager.logger.create_class_logger("PartyState")
        
        # Create party animation - crazy multi-effect on strip 1
        first_strip = game_manager.led_strips[0]
        self.party_anim = PartyAnimation(
            strip=first_strip,
            speed_ms=20  # Very fast updates
        )
        self.animations: List['Animation'] = [self.party_anim]
    
    def custom_on_enter(self) -> None:
        """Actions when entering party mode"""
        # Ignore any currently pressed buttons until they're released
        self.game_manager.button_reader.ignore_pressed_until_released()
        
        # Clear all LED strips from previous animations
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for strip in self.game_manager.led_strips:
            strip[:] = black
            strip.show()
        
        # Play win sound effect
        from audio_system.sound_controller import GameSounds
        self.game_manager.sound_controller.play_sound_with_volume(
            GameSounds.WIN_SOUND, 
            volume=1.0
        )
        
        # Set music to maximum volume
        self.game_manager.sound_controller.mixer.music.set_volume(1.0)
        
        self.logger.info("🎉 PARTY MODE ACTIVATED!")
    
    def custom_on_exit(self) -> None:
        """Stop music when exiting"""
        self.game_manager.sound_controller.stop_music()
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update party state"""
        # Check if song finished playing
        if not self.game_manager.sound_controller.is_song_playing():
            self.logger.info("Song finished, returning to idle")
            return IdleState(self.game_manager)
        
        # Update animations
        for animation in self.animations:
            animation.update_if_needed()
        
        return None


class CodeModeState(GameState):
    """
    Code input mode - user enters a 5-digit code by pressing buttons.
    
    Features:
    - Plays CODE_INPUT_MUSIC on enter
    - Shows pure green light on button segments for entered digits
    - After 5 digits: validates code
    - Valid code → PartyState
    - Any failure → stop music, play fail sound, return to IdleState
    
    Failure conditions:
    1. Invalid/unsupported code
    2. Song ends (timeout)
    3. Any button released
    
    Transitions:
    - Code complete + valid → PartyState
    - Any failure → IdleState
    """
    
    def __init__(self, game_manager: 'GameManager'):
        super().__init__(game_manager)
        
        # Create logger
        self.logger = game_manager.logger.create_class_logger("CodeModeState")
        
        # Create code mode animation on strip 1
        first_strip = game_manager.led_strips[0]
        from game_system.animations import CodeModeAnimation
        self.code_anim = CodeModeAnimation(
            strip=first_strip,
            button_count=game_manager.button_reader.get_button_count(),
            speed_ms=50
        )
        self.animations: List['Animation'] = [self.code_anim]
    
    def custom_on_enter(self) -> None:
        """Actions when entering code mode"""
        # Play code sound effect
        from audio_system.sound_controller import GameSounds
        self.game_manager.sound_controller.play_sound_with_volume(
            GameSounds.CODE_SOUND,
            volume=0.8
        )
        
        # Reset sequence to start fresh
        self.game_manager.sequence_tracker.reset()
        # ignore pressed buttons (the sequence button)
        self.game_manager.button_reader.ignore_pressed_until_released()

        
        # Clear LEDs initially (no digits entered yet)
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for strip in self.game_manager.led_strips:
            strip[:] = black
            strip.show()
        
        # Load and start code input music
        from audio_system.sound_controller import CODE_INPUT_MUSIC_PATH
        self.game_manager.sound_controller.mixer.music.load(CODE_INPUT_MUSIC_PATH)
        self.game_manager.sound_controller.mixer.music.set_volume(0.6)
        self.game_manager.sound_controller.mixer.music.play()
        
        self.logger.info("Entered code mode - awaiting 5-digit code")
    
    def custom_on_exit(self) -> None:
        """Actions when exiting code mode"""
        # Ignore currently pressed buttons until released
        self.game_manager.button_reader.ignore_pressed_until_released()
    
    def _fail_and_return_to_idle(self, reason: str) -> 'GameState':
        """
        Handle code mode failure - stop music, play fail sound, return to idle.
        
        Args:
            reason: Description of why code mode failed (for logging)
            
        Returns:
            IdleState instance
        """
        self.logger.info(f"Code mode failed: {reason}")
        
        # Stop code input music
        self.game_manager.sound_controller.stop_music()
        
        # Play random fail sound
        self.game_manager.sound_controller.play_random_fail_sound(volume=0.8)
        
        # Return to idle
        return IdleState(self.game_manager)
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update code mode - track sequence, check for completion and failures"""
        
        # FAILURE CONDITION 1: Check if any button was released
        # (If a button went from pressed to not pressed)
        for i, currently_pressed in enumerate(button_state.for_button):
            prev_pressed = button_state.previous_state_of[i]
            if prev_pressed and not currently_pressed:
                return self._fail_and_return_to_idle("Button was released")
        
        # FAILURE CONDITION 2: Check if song ended (timeout)
        if not self.game_manager.sound_controller.is_song_playing():
            return self._fail_and_return_to_idle("Timeout - song ended")
        
        # Get current sequence
        sequence = self.game_manager.sequence_tracker.get_sequence()
        
        # Update animation to show entered digits
        self.code_anim.set_active_digits(sequence)
        
        # Check if code is complete (using configured code length)
        code_length = self.game_manager.sound_controller.song_library.code_length
        if len(sequence) == code_length:
            self.logger.info(f"Code entered: {sequence}")
            
            # Validate code
            is_valid = self.game_manager.sound_controller.handle_code(sequence)
            
            if is_valid:
                self.logger.info("Valid code! Transitioning to PartyState")
                # Stop code input music before transitioning
                self.game_manager.sound_controller.stop_music()
                return PartyState(self.game_manager)
            else:
                # FAILURE CONDITION 3: Invalid/unsupported code
                return self._fail_and_return_to_idle(f"Invalid code: {sequence}")
        
        # Update animations
        for animation in self.animations:
            animation.update_if_needed()
        
        return None
