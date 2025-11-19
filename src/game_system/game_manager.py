"""
Main game manager - orchestrates state machine, button input, and LED output
"""

import time
from typing import List, Optional, TYPE_CHECKING

from .states import GameState
from utils import OnceInMs

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

if TYPE_CHECKING:
    from button_system.interfaces import IButtonReader
    from led_system.interfaces import LedStrip
    from button_system.button_state import ButtonState
    from utils import ClassLogger
    from game_system.sequence_tracker import ButtonsSequenceTracker
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
        
        # Memory monitoring using OnceInMs
        self._memory_monitor = OnceInMs(60000)  # Log every 60 seconds
        self._process = psutil.Process() if PSUTIL_AVAILABLE else None
        
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
        
        # 0.1. Log memory usage (once per minute)
        if self._memory_monitor.should_execute():
            self._log_memory_usage()
        
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
        
        # Cleanup sound controller first (properly close ALSA device)
        if hasattr(self, 'sound_controller') and self.sound_controller:
            self.sound_controller.cleanup()
        
        # Clear all LED strips
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for strip in self.led_strips:
            strip[:] = black
            strip.show()
        
        self.logger.info("Game stopped")
    
    def _log_memory_usage(self) -> None:
        """Log current memory and CPU usage (process and system)"""
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            # Process memory info
            mem_info = self._process.memory_info()
            process_mb = mem_info.rss / 1024 / 1024  # Resident Set Size in MB
            
            # Process CPU info (non-blocking)
            process_cpu_percent = self._process.cpu_percent(interval=None)
            
            # System memory info
            sys_mem = psutil.virtual_memory()
            sys_total_mb = sys_mem.total / 1024 / 1024
            sys_used_mb = sys_mem.used / 1024 / 1024
            sys_available_mb = sys_mem.available / 1024 / 1024
            sys_percent = sys_mem.percent
            
            # System CPU info (non-blocking)
            sys_cpu_percent = psutil.cpu_percent(interval=None)
            
            # CPU per core
            cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
            cores_str = ", ".join([f"{cpu:.0f}%" for cpu in cpu_per_core])
            
            self.logger.info(
                f"💾 Memory - Process: {process_mb:.1f}MB | "
                f"System: {sys_used_mb:.0f}/{sys_total_mb:.0f}MB ({sys_percent:.1f}%, "
                f"{sys_available_mb:.0f}MB free) | "
                f"⚙️  CPU - Process: {process_cpu_percent:.1f}% | "
                f"System: {sys_cpu_percent:.1f}% | Cores: [{cores_str}]"
            )
        except Exception as e:
            self.logger.warning(f"Failed to log system usage: {e}")
    
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
