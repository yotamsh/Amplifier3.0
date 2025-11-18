"""
Game state base class and concrete implementations
"""

from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

from .animations import AmplifyAnimation, AnimationDelayWrapper, IdleAnimation, PartyAnimation

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
        success = self.game_manager.sound_controller.load_next_song()
        if not success:
            self.game_manager.logger.warning("⚠️ Could not load next song - audio may not play in next AmplifyState")
    
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
            
        # Check for "777" pattern - enter code mode
        if self.game_manager.sequence_tracker.get_sequence() == "777":
            self.game_manager.logger.info("Triple 777 detected - entering code mode!")
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
    Amplify state - rainbow animations on strip 1, pyramid fill on strip 2.
    
    Strip 1: Each button controls an LED section with rainbow animation.
    Strip 2: Pyramid fills from bottom up based on button count.
    
    Transitions:
    - No buttons pressed → IdleState
    - All buttons pressed → PartyState
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
        
        # Create pyramid animation on strip 2 (index 1)
        from game_system.animations import AmplifyPyramidAnimation
        pyramid_strip = game_manager.led_strips[1]
        self.pyramid_anim = AmplifyPyramidAnimation(
            strip=pyramid_strip,
            button_count=game_manager.button_reader.get_button_count(),
            speed_ms=50  # Fast update for responsive fill
        )
        
        self.animations: List['Animation'] = [self.amplify_anim, self.pyramid_anim]
        
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
        
        # Update animations with current button state
        self.amplify_anim.set_pressed_buttons(self.pressed_buttons)
        self.pyramid_anim.set_pressed_buttons(self.pressed_buttons)
        
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
            # Play win sound before transitioning
            from audio_system.sound_controller import GameSounds
            self.game_manager.sound_controller.play_sound_with_volume(
                GameSounds.WIN_SOUND, 
                volume=1.0
            )
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
            # Update both animations and volume with current button state
            self.amplify_anim.set_pressed_buttons(self.pressed_buttons)
            self.pyramid_anim.set_pressed_buttons(self.pressed_buttons)
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
    - Plays win sound (in AmplifyState before transition)
    - Sets music to maximum volume
    - Strip 1: Crazy multi-effect pushing wave animation
    - Strip 2: Pyramid blinks with random colors every 300ms
    - After 15 seconds: Reduction feature enabled (center buttons can reduce volume/end party)
    - Returns to idle when song ends
    
    Transitions:
    - Song finished → IdleState
    - Reduction complete → IdleState (with BOOM sound)
    """
    
    def __init__(self, game_manager: 'GameManager'):
        super().__init__(game_manager)
        
        # Create logger
        self.logger = game_manager.logger.create_class_logger("PartyState")
        
        # Calculate center buttons for reduction feature
        button_count = game_manager.button_reader.get_button_count()
        self.button_A = button_count // 2
        self.button_B = (button_count - 1) // 2
        first_strip = game_manager.led_strips[0]
        self.leds_per_button = first_strip.num_pixels() // button_count
        
        # Reduction feature state
        self.reduction_enabled = False
        self.party_start_time = None
        self.reduction_enable_delay = 15.0  # seconds
        
        # Red spreading state (number of red pixels from each button)
        self.a_red_pixels = 0  # Red pixels from A side
        self.b_red_pixels = 0  # Red pixels from B side
        self.max_spread = self.button_B * self.leds_per_button
        
        # Spreading timing
        self.spread_interval_ms = 50  # 50ms per pixel
        self.last_spread_time_A = 0
        self.last_spread_time_B = 0
        
        # Button hold state
        self.button_A_held = False
        self.button_B_held = False
        self.button_A_spread_blocked = False  # Blocked due to interference
        self.button_B_spread_blocked = False  # Blocked due to interference
        
        # Last button applause feature (enabled after 15 seconds)
        self.last_button_index = button_count - 1
        self.last_button_held = False
        self.applause_channel = None
        
        # First button amazing feature (enabled after 15 seconds, 10s cooldown)
        self.first_button_index = 0
        self.first_button_held = False
        self.amazing_channel = None
        self.amazing_last_play_time = 0  # Track last play time for throttling
        self.amazing_cooldown = 10.0  # seconds
        
        # Create party animation with reduction support
        self.party_anim = PartyAnimation(
            strip=first_strip,
            speed_ms=20,  # Very fast updates
            button_count=button_count
        )
        
        # Create party pyramid animation on strip 2 (index 1)
        from game_system.animations import PartyPyramidAnimation
        pyramid_strip = game_manager.led_strips[1]
        self.pyramid_party_anim = PartyPyramidAnimation(
            strip=pyramid_strip,
            speed_ms=50  # Check for color changes frequently
        )
        
        self.animations: List['Animation'] = [self.party_anim, self.pyramid_party_anim]
    
    def custom_on_enter(self) -> None:
        """Actions when entering party mode"""
        # Ignore any currently pressed buttons until they're released
        self.game_manager.button_reader.ignore_pressed_until_released()
        
        # Clear all LED strips from previous animations
        from game_system.animation_helpers import AnimationHelpers
        for strip in self.game_manager.led_strips:
            strip[:] = AnimationHelpers.BLACK
            strip.show()
        
        # Set music to maximum volume
        self.game_manager.sound_controller.set_music_volume(1.0)
        
        # Start party timer
        import time
        self.party_start_time = time.time()
        
        self.logger.info("🎉 PARTY MODE ACTIVATED!")
    
    def custom_on_exit(self) -> None:
        """Stop music, applause, and amazing when exiting"""
        self.game_manager.sound_controller.stop_music()
        
        # Stop applause if playing
        if self.applause_channel:
            self.applause_channel.stop()
            self.applause_channel = None
        
        # Stop amazing if playing
        if self.amazing_channel:
            self.amazing_channel.stop()
            self.amazing_channel = None
        
        # Ignore any pressed buttons until they're released
        self.game_manager.button_reader.ignore_pressed_until_released()
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update party state"""
        import time
        current_time = time.time()
        
        # Check if reduction should be enabled
        if not self.reduction_enabled:
            if current_time - self.party_start_time >= self.reduction_enable_delay:
                self.reduction_enabled = True
                self.logger.debug("Reduction feature enabled!")
        
        # Handle reduction logic if enabled
        end_state = None
        if self.reduction_enabled:
            end_state = self._handle_reduction(button_state, current_time)
            if end_state:
                return end_state
            
            # Handle last button applause (also enabled after 15 seconds)
            self._handle_applause_button(button_state)
            
            # Handle first button amazing (also enabled after 15 seconds, with cooldown)
            self._handle_amazing_button(button_state, current_time)
        
        # Check if song finished playing
        if not self.game_manager.sound_controller.is_song_playing():
            self.logger.info("Song finished, returning to idle")
            return IdleState(self.game_manager)
        
        # Update party animation with red override info
        self.party_anim.set_red_override(
            self.button_A,
            self.button_B,
            self.a_red_pixels,
            self.b_red_pixels,
            self.button_A_held,
            self.button_B_held
        )
        
        # Update animations (they handle rendering and show())
        for animation in self.animations:
            animation.update_if_needed()
        
        return None
    
    def _handle_reduction(self, button_state: 'ButtonState', current_time: float) -> Optional['GameState']:
        """
        Handle reduction feature logic.
        
        Returns:
            GameState to transition to, or None to stay in party
        """
        # Track button states
        button_count = len(button_state.for_button)
        button_A_pressed = button_state.for_button[self.button_A]
        button_B_pressed = button_state.for_button[self.button_B]
        
        # Check for interference with button A spread (buttons A+1 to end)
        if self.button_A_held and not self.button_A_spread_blocked:
            for i in range(self.button_A + 1, button_count):
                if button_state.for_button[i]:
                    # Interference detected - clear spread but keep held
                    self.a_red_pixels = 0
                    self.button_A_spread_blocked = True
                    self.logger.debug(f"Button A spread blocked by button {i}")
                    break
        
        # Check for interference with button B spread (buttons 0 to B-1)
        if self.button_B_held and not self.button_B_spread_blocked:
            for i in range(0, self.button_B):
                if button_state.for_button[i]:
                    # Interference detected - clear spread but keep held
                    self.b_red_pixels = 0
                    self.button_B_spread_blocked = True
                    self.logger.debug(f"Button B spread blocked by button {i}")
                    break
        
        # Button A released - clear its red and reset block
        if self.button_A_held and not button_A_pressed:
            self.a_red_pixels = 0
            self.button_A_held = False
            self.button_A_spread_blocked = False  # Reset block on release
            self.last_spread_time_A = 0
        
        # Button B released - clear its red and reset block
        if self.button_B_held and not button_B_pressed:
            self.b_red_pixels = 0
            self.button_B_held = False
            self.button_B_spread_blocked = False  # Reset block on release
            self.last_spread_time_B = 0
        
        # Button A pressed - spread right (segment always red, spread is additional)
        if button_A_pressed:
            if not self.button_A_held:
                self.button_A_held = True
                self.button_A_spread_blocked = False  # Reset block on new press
                self.last_spread_time_A = current_time * 1000
                self.a_red_pixels = 0  # Start at 0 additional spread pixels
            
            # Spread additional pixels every 50ms (only if not blocked)
            if not self.button_A_spread_blocked:
                current_time_ms = current_time * 1000
                if self.a_red_pixels < self.max_spread:
                    if current_time_ms - self.last_spread_time_A >= self.spread_interval_ms:
                        self.a_red_pixels += 1
                        self.last_spread_time_A = current_time_ms
        
        # Button B pressed - spread left (segment always red, spread is additional)
        if button_B_pressed:
            if not self.button_B_held:
                self.button_B_held = True
                self.button_B_spread_blocked = False  # Reset block on new press
                self.last_spread_time_B = current_time * 1000
                self.b_red_pixels = 0  # Start at 0 additional spread pixels
            
            # Spread additional pixels every 50ms (only if not blocked)
            if not self.button_B_spread_blocked:
                current_time_ms = current_time * 1000
                if self.b_red_pixels < self.max_spread:
                    if current_time_ms - self.last_spread_time_B >= self.spread_interval_ms:
                        self.b_red_pixels += 1
                        self.last_spread_time_B = current_time_ms
        
        # Volume control: both pressed AND (n+m) % 10 == 0
        # n+m is ONLY the additional spread pixels, not including segments
        total_spread = self.a_red_pixels + self.b_red_pixels
        both_pressed = button_A_pressed and button_B_pressed
        
        if both_pressed and total_spread % 10 == 0:
            # Volume decreases as spread increases: 1.0 → 0.0
            volume = 1.0 - (total_spread / (2 * self.max_spread))
            self.game_manager.sound_controller.set_music_volume(volume)
        elif not both_pressed:
            # One or none pressed: reset to full volume
            self.game_manager.sound_controller.set_music_volume(1.0)
        
        # End condition: total spread == 2*max_spread
        if total_spread >= 2 * self.max_spread:
            self.logger.info("Reduction complete!")
            from audio_system.sound_controller import GameSounds
            self.game_manager.sound_controller.play_sound_with_volume(
                GameSounds.BOOM_SOUND,
                volume=1.0
            )
            self.game_manager.sound_controller.stop_music()
            return IdleState(self.game_manager)
        
        return None
    
    def _handle_applause_button(self, button_state: 'ButtonState') -> None:
        """
        Handle applause sound for last button.
        When last button is pressed, play applause. When released, stop it.
        """
        last_button_pressed = button_state.for_button[self.last_button_index]
        
        # Button pressed - play applause
        if last_button_pressed and not self.last_button_held:
            self.last_button_held = True
            from audio_system.sound_controller import GameSounds
            self.applause_channel = self.game_manager.sound_controller.play_sound_with_volume(
                GameSounds.APPLAUSE_SOUND,
                volume=1.0
            )
            self.logger.debug("Applause started")
        
        # Button released - stop applause
        elif not last_button_pressed and self.last_button_held:
            self.last_button_held = False
            if self.applause_channel:
                self.applause_channel.stop()
                self.applause_channel = None
            self.logger.debug("Applause stopped")
    
    def _handle_amazing_button(self, button_state: 'ButtonState', current_time: float) -> None:
        """
        Handle amazing sound for first button.
        When first button is pressed, play amazing sound (if cooldown passed).
        When released, stop it. 10-second cooldown between plays.
        """
        first_button_pressed = button_state.for_button[self.first_button_index]
        
        # Button pressed - play amazing (if cooldown passed)
        if first_button_pressed and not self.first_button_held:
            time_since_last_play = current_time - self.amazing_last_play_time
            
            if time_since_last_play >= self.amazing_cooldown:
                self.first_button_held = True
                from audio_system.sound_controller import GameSounds
                self.amazing_channel = self.game_manager.sound_controller.play_sound_with_volume(
                    GameSounds.AMAZING_SOUND,
                    volume=1.0
                )
                self.amazing_last_play_time = current_time
                self.logger.debug("Amazing sound started")
            else:
                # Cooldown not passed, just mark as held without playing
                self.first_button_held = True
                remaining = self.amazing_cooldown - time_since_last_play
                self.logger.debug(f"Amazing sound on cooldown ({remaining:.1f}s remaining)")
        
        # Button released - stop amazing
        elif not first_button_pressed and self.first_button_held:
            self.first_button_held = False
            if self.amazing_channel:
                self.amazing_channel.stop()
                self.amazing_channel = None
            self.logger.debug("Amazing sound stopped")


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
        self.game_manager.sound_controller.load_and_play_special_music(CODE_INPUT_MUSIC_PATH, volume=0.6)
        
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
        
        # Play digit sound if a new button was pressed
        if button_state.any_changed:
            # Check if any button was newly pressed (prev=False, current=True)
            for i, currently_pressed in enumerate(button_state.for_button):
                prev_pressed = button_state.previous_state_of[i]
                if not prev_pressed and currently_pressed:
                    # New button press detected
                    from audio_system.sound_controller import GameSounds
                    self.game_manager.sound_controller.play_sound_with_volume(
                        GameSounds.CODE_DIGIT_SOUND,
                        volume=0.7
                    )
                    break  # Only play once even if multiple buttons pressed
        
        # Update animation to show entered digits
        self.code_anim.set_active_digits(sequence)
        
        # Check if code is complete (using configured code length)
        code_length = self.game_manager.sound_controller.song_library.code_length
        if len(sequence) == code_length:
            self.logger.info(f"Code entered: {sequence}")
            
            # Validate code
            is_valid = self.game_manager.sound_controller.is_code_supported(sequence)
            
            if is_valid:
                self.logger.info("Valid code! Transitioning to CodeRevealState")
                # Stop code input music before transitioning
                self.game_manager.sound_controller.stop_music()
                return CodeRevealState(self.game_manager, sequence, sequence)
            else:
                # FAILURE CONDITION 3: Invalid/unsupported code
                return self._fail_and_return_to_idle(f"Invalid code: {sequence}")
        
        # Update animations
        for animation in self.animations:
            animation.update_if_needed()
        
        return None


class CodeRevealState(GameState):
    """
    Code reveal state - animated transition from valid code entry to party mode.
    
    Sequence:
    1. Play CODE_SOUND on enter, animate code reveal (fill digits progressively)
    2. When CODE_SOUND finishes, play ONE_TWO_THREE_SOUND and switch to blink animation
    3. When ONE_TWO_THREE_SOUND finishes, play song by code and transition to PartyState
    
    Transitions:
    - Song loaded successfully → PartyState
    - Song load failed → IdleState
    """
    
    def __init__(self, game_manager: 'GameManager', code_sequence: str, code: str,
                 fill_speed_ms: int = 200, blink_speed_ms: int = 400):
        """
        Initialize code reveal state.
        
        Args:
            game_manager: GameManager instance
            code_sequence: The button sequence entered (e.g., "314")
            code: The validated code (same as sequence for now)
            fill_speed_ms: Speed of filling animation (ms per digit)
            blink_speed_ms: Speed of blinking animation (ms per cycle)
        """
        super().__init__(game_manager)
        
        # Create logger
        self.logger = game_manager.logger.create_class_logger("CodeRevealState")
        
        # Store code for playing song later
        self.code = code
        self.code_sequence = code_sequence
        
        # Create code reveal animation
        first_strip = game_manager.led_strips[0]
        from game_system.animations import CodeRevealAnimation
        self.reveal_anim = CodeRevealAnimation(
            strip=first_strip,
            button_count=game_manager.button_reader.get_button_count(),
            code_sequence=code_sequence,
            fill_speed_ms=fill_speed_ms,
            blink_speed_ms=blink_speed_ms
        )
        self.animations: List['Animation'] = [self.reveal_anim]
        
        # Sound channel tracking
        self.code_sound_channel = None
        self.one_two_three_channel = None
        
        # Phase tracking
        self.phase = "CODE_SOUND"  # "CODE_SOUND" → "ONE_TWO_THREE" → "LOADING_SONG"
    
    def custom_on_enter(self) -> None:
        """Actions when entering code reveal state"""
        # Clear all LED strips
        from game_system.animation_helpers import AnimationHelpers
        for strip in self.game_manager.led_strips:
            strip[:] = AnimationHelpers.BLACK
            strip.show()
        
        # Play CODE_SOUND and store channel
        from audio_system.sound_controller import GameSounds
        self.code_sound_channel = self.game_manager.sound_controller.play_sound_with_volume(
            GameSounds.CODE_SOUND,
            volume=0.9
        )
        
        self.logger.info(f"Code reveal started for code: {self.code}")
    
    def custom_on_exit(self) -> None:
        """Actions when exiting code reveal state"""
        # Ignore currently pressed buttons until released
        self.game_manager.button_reader.ignore_pressed_until_released()
    
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update code reveal - manage animation phases and sound timing"""
        
        if self.phase == "CODE_SOUND":
            # Phase 1: Wait for CODE_SOUND to finish
            if self.code_sound_channel and not self.code_sound_channel.get_busy():
                # CODE_SOUND finished - play ONE_TWO_THREE_SOUND
                from audio_system.sound_controller import GameSounds
                self.one_two_three_channel = self.game_manager.sound_controller.play_sound_with_volume(
                    GameSounds.ONE_TWO_THREE_SOUND,
                    volume=0.9
                )
                
                # Switch animation to blink mode
                self.reveal_anim.start_blinking()
                
                # Move to next phase
                self.phase = "ONE_TWO_THREE"
                self.logger.debug("CODE_SOUND finished, playing ONE_TWO_THREE sound")
        
        elif self.phase == "ONE_TWO_THREE":
            # Phase 2: Wait for ONE_TWO_THREE_SOUND to finish
            if self.one_two_three_channel and not self.one_two_three_channel.get_busy():
                # Sound finished - play song by code and transition
                self.logger.info(f"Loading song by code: {self.code}")
                
                success = self.game_manager.sound_controller.play_song_by_code(self.code)
                
                self.phase = "LOADING_SONG"
                
                if success:
                    self.logger.info("Song loaded successfully, transitioning to PartyState")
                    return PartyState(self.game_manager)
                else:
                    self.logger.error("Failed to load song, returning to IdleState")
                    return IdleState(self.game_manager)
        
        # Update animations
        for animation in self.animations:
            animation.update_if_needed()
        
        return None
