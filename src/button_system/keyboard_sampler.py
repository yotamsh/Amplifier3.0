"""
Pure keyboard sampler for testing without GPIO hardware
"""

import sys
import select
import termios
import tty
from typing import List

from .interfaces import IButtonSampler


class KeyboardSampler(IButtonSampler):
    """
    Pure keyboard toggle sampler for testing without GPIO.
    
    Simulates button input using keyboard digit keys 0-9 as toggles.
    Works over SSH using stdin (non-blocking select).
    Each keypress toggles that button's state on/off.
    
    Perfect for:
    - Testing on development machines without GPIO hardware
    - Remote debugging over SSH
    - Development on macOS/Linux without Raspberry Pi
    
    Example:
        sampler = KeyboardSampler(
            num_buttons=10,
            logger=logger
        )
        # Now pressing '0' toggles button 0, '1' toggles button 1, etc.
        # Press 'q' to quit (doesn't toggle, just for manual exit in standalone tests)
    """
    
    def __init__(self, 
                 num_buttons: int,
                 logger):
        """
        Initialize keyboard sampler.
        
        Args:
            num_buttons: Number of virtual buttons (max 10 for digit keys 0-9)
            logger: ClassLogger instance for logging
        """
        if num_buttons > 10:
            raise ValueError("KeyboardSampler supports max 10 buttons (digit keys 0-9)")
        
        self._button_count = num_buttons
        self._logger = logger
        self._keyboard_toggles: List[bool] = [False] * num_buttons
        
        # Track if stdin is available and in raw mode
        self._stdin_available = False
        self._original_terminal_settings = None
        self._raw_mode_enabled = False
    
    def _check_stdin_available(self) -> bool:
        """Check if stdin is available for keyboard input"""
        try:
            # Test if stdin is a tty and accessible
            if not sys.stdin.isatty():
                return False
            select.select([sys.stdin], [], [], 0)
            return True
        except Exception:
            return False
    
    def _enable_raw_mode(self) -> bool:
        """
        Enable raw terminal mode for immediate key capture.
        
        Returns:
            True if raw mode enabled successfully, False otherwise
        """
        try:
            # Save original terminal settings
            self._original_terminal_settings = termios.tcgetattr(sys.stdin)
            
            # Enable raw mode (no buffering, no echo)
            tty.setraw(sys.stdin.fileno())
            
            self._raw_mode_enabled = True
            return True
        except Exception as e:
            self._logger.warning(f"Could not enable raw terminal mode: {e}")
            return False
    
    def _disable_raw_mode(self) -> None:
        """Restore original terminal settings"""
        try:
            if self._raw_mode_enabled and self._original_terminal_settings:
                termios.tcsetattr(
                    sys.stdin.fileno(),
                    termios.TCSADRAIN,
                    self._original_terminal_settings
                )
                self._raw_mode_enabled = False
        except Exception:
            pass  # Silent fail during cleanup
    
    def get_button_count(self) -> int:
        """Get number of buttons configured"""
        return self._button_count
    
    def setup(self) -> None:
        """Initialize keyboard input"""
        # Check if stdin is available
        self._stdin_available = self._check_stdin_available()
        
        if not self._stdin_available:
            self._logger.error("❌ Keyboard input not available (stdin not accessible or not a TTY)")
            self._logger.error("   KeyboardSampler requires an interactive terminal")
            raise RuntimeError("Keyboard input not available")
        
        # Enable raw mode for immediate key capture
        if not self._enable_raw_mode():
            self._logger.error("❌ Could not enable raw terminal mode")
            raise RuntimeError("Failed to enable raw terminal mode")
        
        # Log setup success
        self._logger.info("🎮 Keyboard sampler initialized (NO GPIO)")
        self._logger.info(f"   {self._button_count} virtual buttons mapped to digit keys 0-{self._button_count-1}")
        self._logger.info("   Press digit keys to toggle buttons ON/OFF")
        self._logger.info("   Press 'q' to quit (in standalone mode)")
    
    def _check_keyboard_input(self) -> None:
        """
        Check for keyboard input and toggle button states.
        Non-blocking check using select (works over SSH).
        """
        if not self._stdin_available:
            return
        
        try:
            # Non-blocking check for stdin input
            while select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                key = sys.stdin.read(1)
                
                # Handle special keys
                if key == 'q' or key == 'Q':
                    # 'q' for quit - log but don't handle here (let main loop handle)
                    self._logger.info("Keyboard: 'q' pressed (quit key)")
                    continue
                
                if key == ' ':
                    # Space bar - show current state
                    self._show_current_state()
                    continue
                
                if key == 'r' or key == 'R':
                    # 'r' for reset - turn all buttons off
                    self._reset_all_buttons()
                    continue
                
                # Check if it's a digit key
                if key.isdigit():
                    button_index = int(key)
                    
                    # Only toggle if this button exists
                    if button_index < self._button_count:
                        # Toggle the button state
                        self._keyboard_toggles[button_index] = not self._keyboard_toggles[button_index]
                        
                        state_name = "ON" if self._keyboard_toggles[button_index] else "OFF"
                        self._logger.info(f"🎮 Button {button_index} → {state_name} (key '{key}')")
                    else:
                        self._logger.warning(f"Invalid button {button_index} (only 0-{self._button_count-1} available)")
        except Exception as e:
            # Log exceptions but don't interrupt main loop
            self._logger.warning(f"Keyboard input error: {e}")
    
    def _show_current_state(self) -> None:
        """Display current state of all buttons"""
        state_str = " ".join([
            f"{i}:{'ON' if self._keyboard_toggles[i] else 'OFF'}"
            for i in range(self._button_count)
        ])
        self._logger.info(f"Current state: {state_str}")
    
    def _reset_all_buttons(self) -> None:
        """Reset all buttons to OFF state"""
        self._keyboard_toggles = [False] * self._button_count
        self._logger.info("All buttons reset to OFF")
    
    def read_button(self, button_index: int) -> bool:
        """
        Read button state from keyboard toggle.
        
        Checks for keyboard input on each read (non-blocking).
        
        Args:
            button_index: Button number (0-based)
            
        Returns:
            True if button toggle is ON, False if OFF
        """
        # Check for new keyboard input (updates toggles)
        self._check_keyboard_input()
        
        # Return keyboard toggle state
        return self._keyboard_toggles[button_index]
    
    def cleanup(self) -> None:
        """Cleanup keyboard resources and restore terminal"""
        try:
            # Restore terminal settings
            self._disable_raw_mode()
            
            # Reset keyboard toggles
            self._keyboard_toggles = [False] * self._button_count
            
            if self._logger:
                self._logger.info("Keyboard sampler cleaned up")
        except Exception:
            pass  # Silent fail during cleanup
    
    def __del__(self):
        """Automatic cleanup when object is destroyed"""
        self.cleanup()


class KeyboardSamplerLineMode(IButtonSampler):
    """
    Alternative keyboard sampler using line-buffered input.
    
    Unlike KeyboardSampler which uses raw mode, this version reads
    line-buffered input (requires Enter key after each command).
    
    Useful when raw terminal mode is not available or when running
    in environments where stdin is redirected.
    
    Commands:
    - Type digit and press Enter to toggle button
    - Type 'state' and press Enter to see current state
    - Type 'reset' and press Enter to reset all buttons
    - Type 'quit' and press Enter to exit
    """
    
    def __init__(self, num_buttons: int, logger):
        """
        Initialize line-mode keyboard sampler.
        
        Args:
            num_buttons: Number of virtual buttons (max 10)
            logger: ClassLogger instance
        """
        if num_buttons > 10:
            raise ValueError("KeyboardSampler supports max 10 buttons")
        
        self._button_count = num_buttons
        self._logger = logger
        self._keyboard_toggles: List[bool] = [False] * num_buttons
        self._stdin_available = False
    
    def get_button_count(self) -> int:
        """Get number of buttons configured"""
        return self._button_count
    
    def setup(self) -> None:
        """Initialize keyboard input (line mode)"""
        try:
            select.select([sys.stdin], [], [], 0)
            self._stdin_available = True
        except Exception:
            self._stdin_available = False
        
        if not self._stdin_available:
            self._logger.warning("Keyboard input not available")
        else:
            self._logger.info("🎮 Keyboard sampler initialized (LINE MODE - press Enter after each key)")
            self._logger.info(f"   Type 0-{self._button_count-1} and press Enter to toggle")
    
    def read_button(self, button_index: int) -> bool:
        """Read button state (line mode - minimal checking)"""
        # Line mode doesn't actively check on every read
        # User needs to use external input thread or check manually
        return self._keyboard_toggles[button_index]
    
    def toggle_button(self, button_index: int) -> None:
        """Public method to toggle a button (for external input thread)"""
        if 0 <= button_index < self._button_count:
            self._keyboard_toggles[button_index] = not self._keyboard_toggles[button_index]
            state_name = "ON" if self._keyboard_toggles[button_index] else "OFF"
            self._logger.info(f"Button {button_index} → {state_name}")
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self._keyboard_toggles = [False] * self._button_count
        if self._logger:
            self._logger.info("Keyboard sampler (line mode) cleaned up")
    
    def __del__(self):
        """Automatic cleanup"""
        self.cleanup()

