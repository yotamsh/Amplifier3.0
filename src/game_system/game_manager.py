"""
Main game manager - orchestrates state machine, button input, and LED output
"""

import time
from typing import List, Optional, TYPE_CHECKING

from .states import GameState

if TYPE_CHECKING:
    from button_system.interfaces import IButtonReader
    from led_system.interfaces import LedStrip
    from button_system.button_state import ButtonState
    from utils import ClassLogger
    from game_system.sequence_tracker import ButtonsSequenceTracker
else:
    from led_system.pixel import Pixel


class GameManager:
    """
    Main game manager that orchestrates the entire game system.
    
    Responsibilities:
    - Manage state transitions
    - Handle global button sequences  
    - Maintain consistent frame timing
    """
    
    def __init__(self, 
                 button_reader: 'IButtonReader', 
                 led_strips: List['LedStrip'],
                 logger: 'ClassLogger',
                 sound_controller,  # SoundController instance
                 sequence_tracker: 'ButtonsSequenceTracker',
                 frame_duration_ms: int = 20):
        """
        Initialize the game manager.
        
        Args:
            button_reader: Interface for reading button states
            led_strips: List of LED strip controllers
            logger: Logger for debugging and monitoring
            sound_controller: SoundController instance for audio management
            sequence_tracker: ButtonsSequenceTracker instance for tracking button sequences
            frame_duration_ms: Target frame duration in milliseconds (int)
        """
        self.button_reader = button_reader
        self.led_strips = led_strips
        self.sound_controller = sound_controller
        self.sequence_tracker = sequence_tracker
        self.target_frame_duration = frame_duration_ms / 1000.0
        self.logger = logger
        self.running = True
        
        # State management - create initial IdleState
        from game_system.states import IdleState
        self.current_state = IdleState(self)
        
        # Call on_enter for initial state
        self.current_state.on_enter()
        
        self.logger.info(f"GameManager initialized: {frame_duration_ms}ms frame duration, {len(led_strips)} LED strips")
    
    def run_game_loop(self) -> None:
        """
        Run the game loop with automatic frame duration limiting.
        
        This method handles the main game loop and ensures consistent timing.
        Call this from your main() function for automatic frame management.
        """
        self.logger.info(f"Starting game loop with {int(self.target_frame_duration*1000)}ms frame duration")
        
        try:
            while self.running:
                frame_start = time.time()
                
                # Update game state
                self.update()
                
                # Frame duration limiting
                frame_duration = time.time() - frame_start
                sleep_time = self.target_frame_duration - frame_duration
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            self.logger.info("Game stopped by user (Ctrl+C)")
            self.logger.flush()
        except Exception as e:
            self.logger.error(f"Game loop error: {e}", exception=e)
            # Error already auto-flushes, but be explicit
            self.logger.flush()
            raise
        finally:
            self.stop()
    
    def update(self) -> None:
        """
        Main update loop - call this repeatedly in your main loop.
        
        Handles button input, state transitions, and state updates.
        """
        # 0. Update schedule if needed (once per minute)
        self.sound_controller.song_library.update_schedule_if_needed()
        
        # 1. Sample button state
        button_state = self.button_reader.read_buttons()
        
        # 2. Update sequence tracker
        self.sequence_tracker.update(button_state)
        
        # Debug log sequence when new buttons are pressed
        has_new_press = any(
            button_state.was_changed[i] and button_state.for_button[i]
            for i in range(button_state.get_button_count())
        )
        if has_new_press:
            self.logger.debug(f"Button sequence: {self.sequence_tracker.get_sequence()}")
        
        # 3. Let state handle everything and check for state transitions
        new_state = self.current_state.update(button_state)
        if new_state:
            self._transition_to_state(new_state)
    
    def stop(self) -> None:
        """Stop the game and clean up resources."""
        self.running = False
        
        # Clear all LED strips
        black = Pixel(0, 0, 0)
        for strip in self.led_strips:
            strip[:] = black
            strip.show()
        
        self.logger.info("Game stopped")
    
    def _transition_to_state(self, new_state: GameState) -> None:
        """
        Handle transition to a new game state.
        
        Args:
            new_state: The new state to transition to
        """
        
        # Call exit handler on current state
        self.current_state.on_exit()

        # Log state transition
        old_state_name = self.current_state.__class__.__name__
        new_state_name = new_state.__class__.__name__
        self.logger.info(f"State transition: {old_state_name} → {new_state_name}")

        # Switch to new state
        self.current_state = new_state
        
        # Call enter handler on new state
        self.current_state.on_enter()
        
    
    def get_current_state_name(self) -> str:
        """Get the name of the current game state."""
        return self.current_state.__class__.__name__
