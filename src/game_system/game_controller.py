"""
Main game controller - orchestrates state machine, button input, and LED output
"""

import time
from typing import List, Dict, Optional, TYPE_CHECKING

from .base_classes import GameState
from .sequence_detector import SequenceDetector

if TYPE_CHECKING:
    from button_system.interfaces import IButtonReader
    from led_system.interfaces import LedStrip
    from button_system.button_state import ButtonState
    from hybridLogger import ClassLogger


class GameController:
    """
    Main game controller that orchestrates the entire game system.
    
    Responsibilities:
    - Manage state transitions
    - Handle global button sequences  
    - Maintain consistent frame timing
    """
    
    def __init__(self, 
                 button_reader: 'IButtonReader', 
                 led_strips: List['LedStrip'],
                 initial_state: GameState,
                 logger: 'ClassLogger',
                 frame_duration_ms: int = 20,
                 sequence_timeout_ms: int = 1500):
        """
        Initialize the game controller.
        
        Args:
            button_reader: Interface for reading button states
            led_strips: List of LED strip controllers
            initial_state: Starting game state
            logger: Logger for debugging and monitoring
            frame_duration_ms: Target frame duration in milliseconds (int)
            sequence_timeout_ms: Timeout for button sequences
        """
        self.button_reader = button_reader
        self.led_strips = led_strips
        self.target_frame_duration = frame_duration_ms / 1000.0
        self.logger = logger
        self.running = True
        
        # State management
        self.current_state = initial_state
        self.current_state.game_controller = self
        
        # Call on_enter for initial state
        self.current_state.on_enter()
        
        # Global sequence detectors (persist across state transitions)
        self.sequence_detectors: Dict[str, SequenceDetector] = {
            "code_mode": SequenceDetector([7, 7, 7], max_delay_ms=sequence_timeout_ms)
        }
        
        self.logger.info(f"GameController initialized: {frame_duration_ms}ms frame duration, {len(led_strips)} LED strips")
    
    def run_with_frame_limiting(self) -> None:
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
        except Exception as e:
            self.logger.error(f"Game loop error: {e}", exception=e)
            raise
        finally:
            self.stop()
    
    def update(self) -> None:
        """
        Main update loop - call this repeatedly in your main loop.
        
        Handles button input, state transitions, and state updates.
        """
        # 1. Sample button state
        button_state = self.button_reader.read_buttons()
        
        # 2. Check global sequences (before state-specific handling)
        if button_state.any_changed:
            sequence_state = self._check_global_sequences(button_state)
            if sequence_state:
                self._transition_to_state(sequence_state)
                return  # Skip normal state handling after sequence transition
        
        # 3. Let state handle everything and check for state transitions
        new_state = self.current_state.update(button_state)
        if new_state:
            self._transition_to_state(new_state)
    
    def stop(self) -> None:
        """Stop the game and clean up resources."""
        self.running = False
        
        # Clear all LED strips
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for strip in self.led_strips:
            strip[:] = black
            strip.show()
        
        self.logger.info("Game stopped")
    
    def _check_global_sequences(self, button_state) -> Optional[GameState]:
        """
        Check for global button sequences that work across all states.
        
        Args:
            button_state: Current button state with change detection
            
        Returns:
            New GameState if sequence completed, None otherwise
        """
        button_count = self.button_reader.get_button_count()
        
        # Process all button press events
        for i, (was_changed, is_pressed) in enumerate(zip(button_state.was_changed, button_state.for_button)):
            if was_changed and is_pressed:  # Button just pressed
                
                # Basic bounds check
                if i >= button_count:
                    continue
                
                # Check code mode sequence (button 7 pressed 3 times)
                if i == 7:
                    if self.sequence_detectors["code_mode"].add_event(7):
                        self.logger.info("Code mode sequence detected (button 7 x3)")
                        from .states import TestState
                        test_state = TestState()
                        test_state.game_controller = self
                        return test_state
                else:
                    # Any other button press resets the code mode sequence
                    self.sequence_detectors["code_mode"].reset()
        
        return None
    
    def _transition_to_state(self, new_state: GameState) -> None:
        """
        Handle transition to a new game state.
        
        Args:
            new_state: The new state to transition to
        """
        old_state_name = self.current_state.__class__.__name__
        new_state_name = new_state.__class__.__name__
        
        # Call exit handler on current state
        self.current_state.on_exit()
        
        # Switch to new state
        self.current_state = new_state
        
        # Pass game controller reference to new state
        self.current_state.game_controller = self
        
        # Call enter handler on new state
        self.current_state.on_enter()
        
        self.logger.info(f"State transition: {old_state_name} → {new_state_name}")
    
    def get_current_state_name(self) -> str:
        """Get the name of the current game state."""
        return self.current_state.__class__.__name__
