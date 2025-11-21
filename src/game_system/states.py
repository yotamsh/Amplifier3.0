"""
Game state base class and concrete implementations
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TYPE_CHECKING

from .animations import AmplifyAnimation, AmplifySnakeAnimation, AnimationDelayWrapper, HueShiftSnakeAnimation, IdleAnimation, PartyAnimation

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
    
    Architecture:
    - Subclasses register animations via strip_animations dict
    - generic_update_and_show() orchestrates: state logic → animations → rendering
    - Only strips with updated animations call show()
    """
    
    def __init__(self, game_manager: 'GameManager'):
        """Initialize the game state"""
        self.game_manager: 'GameManager' = game_manager
        
        # Track which animation controls which strip (set by subclasses)
        self.strip_animations: Dict[int, Optional['Animation']] = {}
    
    def generic_update_and_show(self, button_state: 'ButtonState') -> Optional['GameState']:
        """
        Generic update orchestration: state logic → animations → rendering.
        
        Call order:
        1. State-specific logic (state_update)
        2. Update all strip animations  
        3. Show() any strips that were modified
        
        Args:
            button_state: Current button state with edge detection
            
        Returns:
            New GameState instance if transition needed, None to stay
        """
        # 1. Let subclass handle state-specific logic
        new_state = self.state_update(button_state)
        
        # 2. Update all strip animations and render
        self._update_and_render_strips()
        
        return new_state
    
    def _update_and_render_strips(self) -> None:
        """Update all registered strip animations and show() those that changed"""
        for strip_index, animation in self.strip_animations.items():
            if animation is not None:
                # Try to update animation buffer
                was_updated = animation.update_if_needed()
                
                # If buffer was modified, push to hardware
                if was_updated:
                    self.game_manager.led_strips[strip_index].show()
    
    @abstractmethod
    def state_update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """
        State-specific update logic (override in subclasses).
        
        Handle button input, check transitions, update state variables.
        DO NOT call animation.update_if_needed() or strip.show() here.
        
        Args:
            button_state: Current button state with edge detection
            
        Returns:
            New GameState instance if transition needed, None to stay
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
        
        # Create class logger for this state
        self.logger = game_manager.logger.create_class_logger("IdleState")
        
        # Register animations for each strip (idle scanner with delay)
        for strip_index, strip in enumerate(self.game_manager.led_strips):
            # Create the appropriate idle animation for each strip
            if strip_index == 0:
                # Button strip: Use new hue-shifting snake animation
                idle_anim = HueShiftSnakeAnimation(
                    strip=strip,
                    speed_ms=25,      # Fast snake movement
                    hue_shift=5,      # Shift trail hue by 5 degrees per frame
                    fade_amount=60    # Trail fading strength
                )
            else:
                # Pyramid strip: Use original IdleAnimation
                idle_anim = IdleAnimation(
                    strip=strip,
                    speed_ms=25,      # Faster scanner movement (was 30ms)
                    hue_increment=5,  # More hue change per frame (was 3)
                    fade_amount=20    # Trail fading strength
                )
            
            # Wrap it with a 2-second delay
            delayed_idle = AnimationDelayWrapper(
                target_animation=idle_anim,
                delay_ms=2000  # 2 seconds of darkness
            )
            
            # Register with base class
            self.strip_animations[strip_index] = delayed_idle
    
    def custom_on_enter(self) -> None:
        """Actions when entering idle state"""
        # Load next random song to be ready for AmplifyState
        success = self.game_manager.sound_controller.load_next_song()
        if not success:
            self.game_manager.logger.warning("⚠️ Could not load next song - audio may not play in next AmplifyState")
    
    def custom_on_exit(self) -> None:
        """Called when exiting idle state - cleanup animations"""
        # Clear animation references to help GC
        for strip_index in list(self.strip_animations.keys()):
            anim = self.strip_animations[strip_index]
            if anim and hasattr(anim, 'strip'):
                anim.strip = None
        self.strip_animations.clear()
        
        # Clear logger reference (prevents logger accumulation)
        self.logger = None
    
    def state_update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update idle state - handle buttons and state transitions"""
        
        # Handle sequence timeout and pattern detection when all buttons released
        if button_state.total_buttons_pressed == 0:
            time_elapsed = self.game_manager.sequence_tracker.get_time_since_first_char()
            
            # Reset sequence if timed out (>2 seconds)
            if time_elapsed is not None and time_elapsed > 3.0:
                self.game_manager.sequence_tracker.reset()
            
        # Check for "777" pattern - enter code mode
        current_sequence = self.game_manager.sequence_tracker.get_sequence()
        if current_sequence == "777":
            self.game_manager.logger.info("Triple 777 detected - entering code mode!")
            self.game_manager.sequence_tracker.reset()
            return CodeModeState(self.game_manager)
        
        # Debug log sequence check (only when buttons are pressed)
        if button_state.total_buttons_pressed > 0 and current_sequence:
            self.logger.debug(f"Checking sequence: '{current_sequence}' (need '777' for code mode)")
        
        # Check for state transitions - any button pressed goes to Amplify
        # ButtonReader handles ignore logic, so this is simple
        if button_state.total_buttons_pressed > 0:
            return AmplifyState(self.game_manager, button_state)
        
        # No transitions - animations will be handled by generic_update_and_show
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
        
        # Create amplify snake animation object on strip 1 (index 0)
        first_strip = game_manager.led_strips[0]
        self.amplify_anim = AmplifySnakeAnimation(
            strip=first_strip,
            button_count=game_manager.button_reader.get_button_count(),
            speed_ms=30  # Fast smooth snake movement
        )
        
        # Create pyramid animation on strip 2 (index 1)
        from game_system.animations import AmplifyPyramidAnimation
        pyramid_strip = game_manager.led_strips[1]
        self.pyramid_anim = AmplifyPyramidAnimation(
            strip=pyramid_strip,
            button_count=game_manager.button_reader.get_button_count(),
            speed_ms=50  # Fast update for responsive fill
        )
        
        # Register animations with base class
        self.strip_animations[0] = self.amplify_anim
        self.strip_animations[1] = self.pyramid_anim
        
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
        
        # Store current song name for logging throughout amplify state
        current_song = self.game_manager.sound_controller.current_song
        self.song_name = os.path.basename(current_song) if current_song else "Unknown"
        
        # Log song started
        self.logger.info(f'Song "{self.song_name}" was randomly started 🎚️')
        
        # Debug logging
        pressed_indexes = [i for i, pressed in enumerate(self.pressed_buttons) if pressed]
        if pressed_indexes:
            self.logger.debug(f"AmplifyState activated with buttons: {pressed_indexes}")
    
    def custom_on_exit(self) -> None:
        """Called when exiting amplify state"""
        # Ignore any currently pressed buttons until they're released
        # This prevents immediately re-entering Amplify if buttons are still held
        self.game_manager.button_reader.ignore_pressed_until_released()
        
        # Clear animation references to help GC
        self.amplify_anim.strip = None
        self.pyramid_anim.strip = None
        self.strip_animations.clear()
        
        # Clear button state references
        self.pressed_buttons = None
        self.initial_button_state = None
        
        # Clear logger reference (prevents logger accumulation)
        self.logger = None
    
    def state_update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update amplify state - handle buttons and state transitions"""
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
            self.logger.info(f'Song "{self.song_name}" was finished while amplifing! 👑')
            self.game_manager.sound_controller.stop_music()
            return IdleState(self.game_manager)
        
        # Check for state transitions - no buttons pressed goes back to Idle
        if button_state.total_buttons_pressed == 0:
            self.logger.info(f'Song "{self.song_name}" was released 🤷🏻‍♀️')
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
        
        # No transitions - animations will be handled by generic_update_and_show
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
        
        # Track special buttons (excluded from dot firing)
        self.special_buttons = {0, button_count - 1, self.button_A, self.button_B}  # First, last, A, B
        
        # Button hold tracking for tap/hold/charge detection
        self.button_hold_states = {}  # Dict[button_index, hold_info]
        
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
        self.amazing_last_play_time = 0  # Track last play time for throttling
        self.amazing_cooldown = 10.0  # seconds
        
        # Create party animation with reduction support
        self.party_anim = PartyAnimation(
            strip=first_strip,
            speed_ms=20,  # Very fast updates
            button_count=button_count
        )
        
        # Create party pyramid animation sequence on strip 2 (index 1) with red override
        from game_system.animations import create_party_pyramid_animation
        pyramid_strip = game_manager.led_strips[1]
        # Pass max_spread for red override calculation
        self.pyramid_party_anim = create_party_pyramid_animation(pyramid_strip, max_spread=self.max_spread)
        
        # Register animations with base class
        self.strip_animations[0] = self.party_anim
        self.strip_animations[1] = self.pyramid_party_anim
    
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
        
        # Store current song name for logging throughout party state
        current_song = self.game_manager.sound_controller.current_song
        self.song_name = os.path.basename(current_song) if current_song else "Unknown"
        
        self.logger.info(f"🎉 PARTY MODE ACTIVATED for song: {self.song_name}")
    
    def custom_on_exit(self) -> None:
        """Stop music and applause when exiting"""
        self.game_manager.sound_controller.stop_music()
        
        # Stop and clear applause channel
        if self.applause_channel:
            self.applause_channel.stop()
            self.applause_channel = None
        
        # Clear animation references to help GC
        self.party_anim.strip = None
        self.pyramid_party_anim.strip = None
        self.strip_animations.clear()
        
        # Clear logger reference (prevents logger accumulation)
        self.logger = None
        
        # Ignore any pressed buttons until they're released
        self.game_manager.button_reader.ignore_pressed_until_released()
    
    def state_update(self, button_state: 'ButtonState') -> Optional['GameState']:
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
        
        # Handle button hold effects for non-special buttons (any time during party)
        button_count = len(button_state.for_button)
        for i in range(button_count):
            if i in self.special_buttons:
                continue
            
            currently_pressed = button_state.for_button[i]
            was_pressed = button_state.previous_state_of[i]
            
            # RISING EDGE: Button just pressed
            if not was_pressed and currently_pressed:
                self.button_hold_states[i] = {
                    'start_time': current_time,
                    'last_stream_fire': current_time,
                    'is_charging': False,
                    'charge_level': 0.0
                }
                # Fire initial dot (tap)
                self.party_anim.trigger_dot(i, dot_type='normal')
                self.logger.debug(f"Button {i} pressed - initial dot fired")
            
            # HELD: Button still pressed
            elif was_pressed and currently_pressed:
                hold_info = self.button_hold_states.get(i)
                if hold_info:
                    hold_duration = current_time - hold_info['start_time']
                    
                    # STREAM MODE (0.3s - 2s)
                    if 0.3 <= hold_duration < 2.0:
                        # Fire stream particles every 0.15s
                        if current_time - hold_info['last_stream_fire'] >= 0.15:
                            self.party_anim.trigger_dot(i, dot_type='stream')
                            hold_info['last_stream_fire'] = current_time
                    
                    # CHARGE MODE (> 2s)
                    elif hold_duration >= 2.0:
                        if not hold_info['is_charging']:
                            hold_info['is_charging'] = True
                            self.logger.debug(f"Button {i} charging mode activated")
                        
                        # Charge level increases: 0 at 2s, 1.0 at 5s
                        hold_info['charge_level'] = min(1.0, (hold_duration - 2.0) / 3.0)
                        # Update charging visual on button segment
                        self.party_anim.set_button_charge(i, hold_info['charge_level'])
            
            # FALLING EDGE: Button released
            elif was_pressed and not currently_pressed:
                hold_info = self.button_hold_states.get(i)
                if hold_info:
                    hold_duration = current_time - hold_info['start_time']
                    
                    # Quick tap (< 0.3s): Already fired single dot
                    if hold_duration < 0.3:
                        pass  # Single dot already fired on press
                    
                    # Release from charge (> 2s): Fire explosion
                    elif hold_duration >= 2.0:
                        explosion_power = hold_info['charge_level']
                        self.party_anim.trigger_explosion(i, explosion_power)
                        self.logger.info(f"Button {i} explosion! Power: {explosion_power:.2f}")
                    
                    # Release from stream (0.3s - 2s): Small burst
                    else:
                        self.party_anim.trigger_dot(i, dot_type='burst')
                        self.logger.debug(f"Button {i} stream burst")
                    
                    # Clear hold state
                    self.party_anim.clear_button_charge(i)
                    del self.button_hold_states[i]
        
        # Check if song finished playing
        if not self.game_manager.sound_controller.is_song_playing():
            self.logger.info(f"Song finished, returning to idle: {self.song_name}")
            return IdleState(self.game_manager)
        
        # Update party animation with red override info (strip 0)
        self.party_anim.set_red_override(
            self.button_A,
            self.button_B,
            self.a_red_pixels,
            self.b_red_pixels,
            self.button_A_held,
            self.button_B_held
        )
        
        # Update pyramid animation with red override (strip 1)
        self.pyramid_party_anim.set_red_override(self.a_red_pixels, self.b_red_pixels)
        
        # No transitions - animations will be handled by generic_update_and_show
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
            self.logger.info(f'Party Mode for song "{self.song_name}" was quite-down! 🤫')
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
        When first button is pressed (edge detection), play amazing sound if cooldown passed.
        Sound plays to completion regardless of button state. 10-second cooldown between plays.
        """
        first_button_pressed = button_state.for_button[self.first_button_index]
        first_button_prev = button_state.previous_state_of[self.first_button_index]
        
        # Detect button press edge (prev=False, current=True)
        if not first_button_prev and first_button_pressed:
            time_since_last_play = current_time - self.amazing_last_play_time
            
            if time_since_last_play >= self.amazing_cooldown:
                # Cooldown passed - play sound
                from audio_system.sound_controller import GameSounds
                self.game_manager.sound_controller.play_sound_with_volume(
                    GameSounds.AMAZING_SOUND,
                    volume=1.0
                )
                self.amazing_last_play_time = current_time
                self.logger.debug("Amazing sound started")
            else:
                # Cooldown not passed
                remaining = self.amazing_cooldown - time_since_last_play
                self.logger.debug(f"Amazing sound on cooldown ({remaining:.1f}s remaining)")


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
        
        # Create code mode animation on strip 0 (button strip)
        first_strip = game_manager.led_strips[0]
        from game_system.animations import CodeModeAnimation
        self.code_anim = CodeModeAnimation(
            strip=first_strip,
            button_count=game_manager.button_reader.get_button_count(),
            speed_ms=50
        )
        
        # Create code mode pyramid animation on strip 1 (pyramid)
        from game_system.animations import CodeModePyramidAnimation
        pyramid_strip = game_manager.led_strips[1]
        self.pyramid_code_anim = CodeModePyramidAnimation(
            strip=pyramid_strip,
            speed_ms=20
        )
        
        # Register with base class
        self.strip_animations[0] = self.code_anim
        self.strip_animations[1] = self.pyramid_code_anim
    
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
        
        # Clear animation references to help GC
        self.code_anim.strip = None
        self.pyramid_code_anim.strip = None
        self.strip_animations.clear()
        
        # Clear logger reference (prevents logger accumulation)
        self.logger = None
    
    def _fail_and_return_to_idle(self, reason: str, released_button: int = None) -> 'GameState':
        """
        Handle code mode failure - transition to CodeFailState.
        
        Args:
            reason: Description of why code mode failed (for logging)
            released_button: Button index that was released (if applicable)
            
        Returns:
            CodeFailState instance (which will handle sound, animations, and transition to idle)
        """
        # Get current sequence
        sequence = self.game_manager.sequence_tracker.get_sequence()
        
        # Transition to fail state (which will handle music, sound, and animations)
        return CodeFailState(
            self.game_manager, 
            fail_reason=reason,
            sequence=sequence,
            released_button=released_button
        )
    
    def state_update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update code mode - track sequence, check for completion and failures"""
        
        # FAILURE CONDITION 1: Check if any button was released
        # (If a button went from pressed to not pressed)
        for i, currently_pressed in enumerate(button_state.for_button):
            prev_pressed = button_state.previous_state_of[i]
            if prev_pressed and not currently_pressed:
                return self._fail_and_return_to_idle("Button was released", released_button=i)
        
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
                self.logger.debug("Valid code! Transitioning to CodeRevealState")
                # Stop code input music before transitioning
                self.game_manager.sound_controller.stop_music()
                return CodeRevealState(self.game_manager, sequence, sequence)
            else:
                # FAILURE CONDITION 3: Invalid/unsupported code
                return self._fail_and_return_to_idle(f"Invalid code: {sequence}")
        
        # No transitions - animations will be handled by generic_update_and_show
        return None


class CodeRevealState(GameState):
    """
    Code reveal state - animated transition from valid code entry to party mode.
    
    Sequence:
    1. Play CODE_SOUND on enter, animate code reveal (fill digits progressively, then blink)
    2. When CODE_SOUND finishes, play ONE_TWO_THREE_SOUND (animation continues blinking)
    3. When ONE_TWO_THREE_SOUND finishes, play song by code and transition to PartyState
    
    Animation automatically transitions from fill → blink using SequenceAnimation.
    
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
            fill_speed_ms: Speed of filling animation (ms per digit) - unused, kept for compatibility
            blink_speed_ms: Speed of blinking animation (ms per cycle) - unused, kept for compatibility
        """
        super().__init__(game_manager)
        
        # Create logger
        self.logger = game_manager.logger.create_class_logger("CodeRevealState")
        
        # Store code for playing song later
        self.code = code
        self.code_sequence = code_sequence
        
        # Create code reveal animations using factory functions
        first_strip = game_manager.led_strips[0]
        pyramid_strip = game_manager.led_strips[1]
        
        from game_system.animations import (create_code_reveal_button_animation, 
                                            create_code_reveal_pyramid_animation)
        
        self.reveal_anim = create_code_reveal_button_animation(
            strip=first_strip,
            button_count=game_manager.button_reader.get_button_count(),
            code_sequence=code_sequence
        )
        
        self.pyramid_reveal_anim = create_code_reveal_pyramid_animation(
            strip=pyramid_strip, 
            code_sequence=code_sequence
        )
        
        # Register with base class
        self.strip_animations[0] = self.reveal_anim
        self.strip_animations[1] = self.pyramid_reveal_anim
        
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
        
        # Get song name for logging
        song_path = self.game_manager.sound_controller.song_library.get_song_by_code(self.code)
        song_name = os.path.basename(song_path) if song_path else "Unknown"
        
        self.logger.info(f'Code reveal started for code: {self.code} for song "{song_name}"')
    
    def custom_on_exit(self) -> None:
        """Actions when exiting code reveal state"""
        # Ignore currently pressed buttons until released
        self.game_manager.button_reader.ignore_pressed_until_released()
        
        # Clear animation references to help GC
        self.strip_animations.clear()
        
        # Clear sound channel references
        self.code_sound_channel = None
        self.one_two_three_channel = None
        
        # Clear logger reference (prevents logger accumulation)
        self.logger = None
    
    def state_update(self, button_state: 'ButtonState') -> Optional['GameState']:
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
                
                # Animation automatically transitions from fill to blink via SequenceAnimation
                # No need to manually switch phases
                
                # Move to next phase
                self.phase = "ONE_TWO_THREE"
                self.logger.debug("CODE_SOUND finished, playing ONE_TWO_THREE sound")
        
        elif self.phase == "ONE_TWO_THREE":
            # Phase 2: Wait for ONE_TWO_THREE_SOUND to finish
            if self.one_two_three_channel and not self.one_two_three_channel.get_busy():
                # Sound finished - play song by code and transition
                success = self.game_manager.sound_controller.play_song_by_code(self.code)
                
                self.phase = "LOADING_SONG"
                
                if success:
                    return PartyState(self.game_manager)
                else:
                    self.logger.error("Failed to load song, returning to IdleState")
                    return IdleState(self.game_manager)
        
        # No transitions - animations will be handled by generic_update_and_show
        return None


class CodeFailState(GameState):
    """
    Code failure state - shows failure animation and plays fail sound.
    
    Displays red failure animation on both strips,
    plays fail sound based on reason, then transitions back to IdleState.
    
    Button strip behavior:
    - Button released: Sequence buttons stay green, released button blinks red
    - Other failures: Only sequence buttons light red
    
    Pyramid strip: Always lights entire strip red
    
    Fail sounds:
    - Button released: ReleasedTheButton.mp3
    - Wrong code: fail2.mp3
    - Timeout: fail4.mp3
    
    Transitions:
    - After sound finishes → IdleState
    """
    
    def __init__(self, game_manager: 'GameManager', fail_reason: str, 
                 sequence: str = "", released_button: int = None):
        """
        Initialize code fail state.
        
        Args:
            game_manager: GameManager instance
            fail_reason: Description of why code entry failed
            sequence: The sequence entered so far (for button strip animation)
            released_button: Button index that was released (if applicable)
        """
        super().__init__(game_manager)
        
        # Create logger
        self.logger = game_manager.logger.create_class_logger("CodeFailState")
        
        # Store fail reason and details for logging
        self.fail_reason = fail_reason
        self.sequence = sequence
        self.released_button = released_button
        
        # Convert sequence to button indices
        sequence_buttons = []
        for char in sequence:
            if char.isdigit():
                sequence_buttons.append(int(char))
        
        # Create failure animations based on fail reason
        from game_system.animations import (create_failure_animation, 
                                            create_button_released_failure_animation)
        
        first_strip = game_manager.led_strips[0]
        button_count = game_manager.button_reader.get_button_count()
        
        # Determine if this is a button-released failure
        is_button_released = "released" in fail_reason.lower()
        
        if is_button_released and released_button is not None:
            # Button released: green sequence + blinking red on released button
            self.fail_anim_strip0 = create_button_released_failure_animation(
                first_strip,
                sequence_buttons=sequence_buttons,
                released_button=released_button,
                button_count=button_count
            )
        else:
            # Other failures: red only on sequence segments
            self.fail_anim_strip0 = create_failure_animation(
                first_strip, 
                sequence_buttons=sequence_buttons,
                button_count=button_count
            )
        
        # Pyramid strip: always show red on entire strip
        pyramid_strip = game_manager.led_strips[1]
        self.fail_anim_strip1 = create_failure_animation(pyramid_strip)
        
        # Register with base class
        self.strip_animations[0] = self.fail_anim_strip0
        self.strip_animations[1] = self.fail_anim_strip1
        
        # Sound channel tracking (exit when sound ends)
        self.fail_sound_channel = None
    
    def custom_on_enter(self) -> None:
        """Actions when entering code fail state"""
        self.logger.info(f"Code mode failed: {self.fail_reason}")
        
        # Stop code input music
        self.game_manager.sound_controller.stop_music()
        
        # Don't clear strips - animations will render immediately, preserving smooth transition
        
        # Play appropriate fail sound based on reason
        from audio_system.sound_controller import GameSounds
        
        if "released" in self.fail_reason.lower():
            # Button was released
            sound = GameSounds.RELEASED_BUTTON_SOUND
            self.logger.debug("Playing ReleasedTheButton sound")
        elif "invalid code" in self.fail_reason.lower() or "unsupported" in self.fail_reason.lower():
            # Wrong code
            sound = GameSounds.FAIL_SOUND_2
            self.logger.debug("Playing fail2 sound (wrong code)")
        elif "timeout" in self.fail_reason.lower() or "song ended" in self.fail_reason.lower():
            # Timeout
            sound = GameSounds.FAIL_SOUND_4
            self.logger.debug("Playing fail4 sound (timeout)")
        else:
            # Default to fail2
            sound = GameSounds.FAIL_SOUND_2
            self.logger.debug("Playing fail2 sound (default)")
        
        # Play the selected sound and store channel
        self.fail_sound_channel = self.game_manager.sound_controller.play_sound_with_volume(
            sound,
            volume=0.8
        )
    
    def custom_on_exit(self) -> None:
        """Actions when exiting code fail state"""
        # Ignore currently pressed buttons until released
        self.game_manager.button_reader.ignore_pressed_until_released()
        
        # Clear animation references to help GC
        self.strip_animations.clear()
        
        # Clear sound channel reference
        self.fail_sound_channel = None
        
        # Clear logger reference (prevents logger accumulation)
        self.logger = None
    
    def state_update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """Update code fail state - wait for sound to finish before transitioning"""
        
        # Check if fail sound has finished playing
        if self.fail_sound_channel and not self.fail_sound_channel.get_busy():
            self.logger.debug("Failure sound complete, returning to IdleState")
            return IdleState(self.game_manager)
        
        # No transitions yet - animations will be handled by generic_update_and_show
        return None
