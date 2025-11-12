"""
GPIO-based button reader implementation using RPi.GPIO
"""

import sys
from typing import List

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("⚠️  RPi.GPIO not available - this module is for Raspberry Pi only")
    # Don't exit here - allow imports for testing/development on other platforms

from .interfaces import IButtonReader
from .button_state import ButtonState

class ButtonReader(IButtonReader):
    """
    RPi.GPIO implementation of button reader with no software debouncing.
    
    Reads raw GPIO states and provides edge detection through state comparison.
    Follows Dependency Inversion Principle by accepting logger abstraction.
    
    Example:
        main_logger = HybridLogger("buttons")
        logger = main_logger.get_class_logger("ButtonReader", logging.INFO)
        reader = ButtonReader([25, 24, 23], logger)
        
        while True:
            state = reader.read_buttons()
            if state.any_changed:
                logger.info(f"Buttons changed: {state}")
    """
    
    def __init__(self, 
                 button_pins: List[int], 
                 logger,  # ClassLogger instance from HybridLogger.get_class_logger()
                 pull_mode: int = None):
        """
        Initialize GPIO button reader.
        
        Args:
            button_pins: List of GPIO pin numbers (BCM mode) 
                        e.g., [25, 24, 23] means button 0=GPIO25, button 1=GPIO24, etc.
            logger: ClassLogger instance from HybridLogger.get_class_logger()
            pull_mode: GPIO pull resistor mode (GPIO.PUD_OFF, GPIO.PUD_UP, GPIO.PUD_DOWN)
                      Defaults to GPIO.PUD_OFF (no internal pulls)
        """
        if 'RPi.GPIO' not in sys.modules:
            raise ImportError("RPi.GPIO is required but not available")
            
        self._button_pins = button_pins.copy()  # Defensive copy
        self._logger = logger
        self._pull_mode = pull_mode if pull_mode is not None else GPIO.PUD_OFF
        
        # Initialize previous state (all buttons start as not-pressed)
        self._previous_state: List[bool] = [False] * len(button_pins)
        
        # Track buttons to ignore until released
        self._ignored_buttons: List[bool] = [False] * len(button_pins)  # True = ignore this button
        
        # Setup GPIO hardware  
        self._gpio_initialized = False  # Track if GPIO was successfully initialized
        self._setup_gpio()
        
        self._logger.info(f"ButtonReader initialized with {len(button_pins)} buttons")
        self._logger.info(f"Button mapping: {self._get_pin_mapping()}")
    
    def _get_pin_mapping(self) -> str:
        """Get human-readable pin mapping for logging"""
        mapping = []
        for idx, pin in enumerate(self._button_pins):
            mapping.append(f"Button{idx}=GPIO{pin}")
        return ", ".join(mapping)
    
    def _setup_gpio(self) -> None:
        """Initialize GPIO pins for button input"""
        try:
            # Set BCM mode (using GPIO pin numbers, not physical pin numbers)
            GPIO.setmode(GPIO.BCM)
            
            # Configure each button pin as input
            for pin in self._button_pins:
                GPIO.setup(pin, GPIO.IN, pull_up_down=self._pull_mode)
            
            self._gpio_initialized = True  # Mark as successfully initialized
            
            pull_mode_name = {
                GPIO.PUD_OFF: "no pulls",
                GPIO.PUD_UP: "pull-up", 
                GPIO.PUD_DOWN: "pull-down"
            }.get(self._pull_mode, f"mode_{self._pull_mode}")
            
            self._logger.info(f"GPIO setup complete: {len(self._button_pins)} pins, {pull_mode_name}")
            
        except Exception as e:
            self._logger.error(f"GPIO setup failed: {e}")
            raise
    
    def ignore_pressed_until_released(self) -> None:
        """
        Mark currently pressed buttons to be ignored until they are released.
        
        Uses the current raw button state to determine which buttons to ignore.
        Once ignored, a button will report as "not pressed" in read_buttons()
        until it is physically released, then it will work normally again.
        
        Example:
            # After entering PartyState with buttons still held:
            button_reader.ignore_pressed_until_released()
            # Now those held buttons won't trigger transitions until released and re-pressed
        """
        # Read current raw GPIO state
        for i, pin in enumerate(self._button_pins):
            gpio_value = GPIO.input(pin)
            button_pressed = (gpio_value == GPIO.HIGH)
            
            if button_pressed:
                self._ignored_buttons[i] = True
                self._logger.debug(f"Button {i} will be ignored until released")
    
    def read_buttons(self) -> ButtonState:
        """
        Read current state of all buttons with ignore filtering.
        
        Buttons marked as "ignored" will report as not pressed until they are
        physically released, then they return to normal behavior.
        
        Returns:
            ButtonState: Complete state with current/previous values and edge detection
        """
        # Read current state from all GPIO pins (raw hardware state)
        raw_current_state: List[bool] = []
        for pin in self._button_pins:
            gpio_value = GPIO.input(pin)
            button_pressed = (gpio_value == GPIO.HIGH)
            raw_current_state.append(button_pressed)
        
        # Apply ignore filtering
        filtered_current_state: List[bool] = []
        for i, is_pressed in enumerate(raw_current_state):
            if self._ignored_buttons[i]:
                # This button is being ignored
                if not is_pressed:
                    # Button was released! Stop ignoring it
                    self._ignored_buttons[i] = False
                    self._logger.debug(f"Button {i} released, no longer ignored")
                    filtered_current_state.append(False)
                else:
                    # Button still pressed, keep ignoring (report as not pressed)
                    filtered_current_state.append(False)
            else:
                # Not ignored, report actual state
                filtered_current_state.append(is_pressed)
        
        # Create comprehensive state object using filtered state
        state = ButtonState(
            for_button=filtered_current_state,
            previous_state_of=self._previous_state.copy()
        )
        
        # Update previous state with FILTERED state (important!)
        self._previous_state = filtered_current_state.copy()
        
        # Log significant changes
        if state.any_changed:
            changed_buttons = [
                (i, "pressed" if state.for_button[i] else "released") 
                for i, changed in enumerate(state.was_changed) if changed]
            self._logger.debug(f"Button state changed: {changed_buttons}")
        
        return state
    
    def get_button_count(self) -> int:
        """Get number of buttons configured in this reader"""
        return len(self._button_pins)
    
    def get_button_pins(self) -> List[int]:
        """Get copy of GPIO pin list for debugging/inspection"""
        return self._button_pins.copy()
    
    def cleanup(self) -> None:
        """
        Optional manual cleanup for advanced users.
        Automatic cleanup happens via __del__ so this is not required.
        """
        self._cleanup_gpio()
    
    def _cleanup_gpio(self) -> None:
        """Internal cleanup method - safe for automatic calling"""
        try:
            # Only cleanup if GPIO was actually initialized
            if hasattr(self, '_gpio_initialized') and self._gpio_initialized:
                GPIO.cleanup()
                self._gpio_initialized = False  # Mark as cleaned up
                # Only log if logger still exists (may be destroyed during shutdown)
                if hasattr(self, '_logger') and self._logger:
                    self._logger.info("GPIO resources cleaned up successfully")
        except Exception:
            # Silent fail during destruction - logging system may be gone
            pass
    
    def __del__(self):
        """Automatic cleanup when object is destroyed"""
        self._cleanup_gpio()
