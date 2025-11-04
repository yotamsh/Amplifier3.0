"""
Main game controller - orchestrates state machine, button input, and LED output
"""

import time
from typing import List, Dict, Optional, TYPE_CHECKING

from .base_classes import GameState
from .sequence_detector import SequenceDetector
from .states import IdleState
from .config import GameConfig

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
    - Coordinate LED strip updates
    - Maintain consistent frame timing
    """
    
    def __init__(self, 
                 button_reader: 'IButtonReader', 
                 led_strips: List['LedStrip'],
                 config: GameConfig,
                 logger: Optional['ClassLogger'] = None):
        """
        Initialize the game controller.
        
        Args:
            button_reader: Interface for reading button states
            led_strips: List of LED strip controllers
            config: Game configuration
            logger: Optional logger for debugging and monitoring
        """
        config.validate()  # Basic validation
        
        self.button_reader: 'IButtonReader' = button_reader
        self.led_strips: List['LedStrip'] = led_strips
        self.config: GameConfig = config
        self.target_frame_time: float = config.frame_duration_ms / 1000.0
        self.logger: Optional['ClassLogger'] = logger
        
        # State management
        self.current_state: GameState = IdleState()
        self.current_state.config = config  # Pass config to state
        self.running: bool = True
        
        # Global sequence detectors (persist across state transitions)
        self.sequence_detectors: Dict[str, SequenceDetector] = {
            "code_mode": SequenceDetector([7, 7, 7], max_delay_ms=config.sequence_timeout_ms)
        }
        
        # Timing and performance tracking
        self.last_update_time: float = time.time()
        self.frame_count: int = 0
        self.total_frame_time: float = 0.0
        
        if self.logger:
            self.logger.info(f"GameController initialized: {config.target_fps:.1f} FPS target, {len(led_strips)} LED strips")
    
    def update(self) -> None:
        """
        Main update loop - call this repeatedly in your main loop.
        
        Handles button input, state transitions, animation updates, and LED rendering.
        """
        frame_start_time = time.time()
        current_time = frame_start_time
        dt = current_time - self.last_update_time
        self.last_update_time = current_time
        
        try:
            # 1. Sample button state
            button_state: 'ButtonState' = self.button_reader.read_buttons()
            
            # 2. Check global sequences (before state-specific handling)
            if button_state.any_changed:
                sequence_state = self._check_global_sequences(button_state)
                if sequence_state:
                    self._transition_to_state(sequence_state)
                    return  # Skip normal state handling after sequence transition
            
            # 3. Handle state-specific button changes
            if button_state.any_changed:
                new_state = self.current_state.handle_button_change(button_state)
                if new_state:
                    self._transition_to_state(new_state)
            
            # 4. Update current state and animations
            self.current_state.update(dt)
            
            # 5. Render to LED strips
            self.current_state.render(self.led_strips)
            
            # 6. Show LED updates (blocking operation)
            for strip in self.led_strips:
                strip.show()
            
            # 7. Track performance
            self._track_performance(frame_start_time)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in game update loop: {e}", exception=e)
            raise
    
    def _check_global_sequences(self, button_state: 'ButtonState') -> Optional[GameState]:
        """
        Check for global button sequences that work across all states.
        
        Args:
            button_state: Current button state with change detection
            
        Returns:
            New GameState if sequence completed, None otherwise
        """
        # Process all button press events
        for i, (was_changed, is_pressed) in enumerate(zip(button_state.was_changed, button_state.for_button)):
            if was_changed and is_pressed:  # Button just pressed
                
                # Basic bounds check
                if i >= self.config.button_count:
                    continue
                
                # Check code mode sequence (button 7 pressed 3 times)
                if i == 7:
                    if self.sequence_detectors["code_mode"].add_event(7):
                        if self.logger:
                            self.logger.info("Code mode sequence detected (button 7 x3)")
                        from .states import TestState
                        test_state = TestState()
                        test_state.config = self.config
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
        if hasattr(self.current_state, 'on_exit'):
            self.current_state.on_exit()
        
        # Switch to new state
        self.current_state = new_state
        
        # Pass config to new state
        if hasattr(self.current_state, 'config'):
            self.current_state.config = self.config
        
        # Call enter handler on new state
        if hasattr(self.current_state, 'on_enter'):
            self.current_state.on_enter()
        
        if self.logger:
            self.logger.info(f"State transition: {old_state_name} → {new_state_name}")
    
    def _track_performance(self, frame_start_time: float) -> None:
        """
        Track frame timing and performance metrics.
        
        Args:
            frame_start_time: Time when frame processing started
        """
        frame_end_time = time.time()
        frame_duration = frame_end_time - frame_start_time
        
        self.frame_count += 1
        self.total_frame_time += frame_duration
        
        # Log performance warnings
        if frame_duration > self.target_frame_time * 1.5:
            if self.logger:
                self.logger.warning(
                    f"Frame took {frame_duration*1000:.1f}ms "
                    f"(target: {self.target_frame_time*1000:.1f}ms)"
                )
        
        # Log periodic performance stats (every 10 seconds)  
        if self.frame_count % (int(self.config.target_fps) * 10) == 0:
            avg_frame_time = self.total_frame_time / self.frame_count
            actual_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
            
            if self.logger:
                self.logger.info(
                    f"Performance: {actual_fps:.1f} FPS "
                    f"(avg frame: {avg_frame_time*1000:.1f}ms)"
                )
    
    def run_with_frame_limiting(self) -> None:
        """
        Run the game loop with automatic frame rate limiting.
        
        This method handles the main game loop and ensures consistent timing.
        Call this from your main() function for automatic frame management.
        """
        if self.logger:
            self.logger.info(f"Starting game loop at {self.config.target_fps:.1f} FPS")
        
        try:
            while self.running:
                frame_start = time.time()
                
                # Update game state
                self.update()
                
                # Frame rate limiting
                frame_duration = time.time() - frame_start
                sleep_time = self.target_frame_time - frame_duration
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            if self.logger:
                self.logger.info("Game stopped by user (Ctrl+C)")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Game loop error: {e}", exception=e)
            raise
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the game and clean up resources."""
        self.running = False
        
        # Clear all LED strips
        try:
            from led_system.pixel import Pixel
            black = Pixel(0, 0, 0)
            for strip in self.led_strips:
                strip[:] = black
                strip.show()
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error clearing LED strips: {e}")
        
        if self.logger:
            avg_fps = self.frame_count / self.total_frame_time if self.total_frame_time > 0 else 0
            self.logger.info(
                f"Game stopped. Final stats: {self.frame_count} frames, "
                f"{avg_fps:.1f} average FPS"
            )
    
    def get_current_state_name(self) -> str:
        """Get the name of the current game state."""
        return self.current_state.__class__.__name__
    
    def force_state_transition(self, new_state: GameState) -> None:
        """Force transition to a specific state (for debugging/testing)."""
        self._transition_to_state(new_state)
