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
    
    def read_buttons(self) -> ButtonState:
        """
        Read current state of all buttons and return comprehensive state.
        
        Performs raw GPIO reads with no software debouncing.
        Edge detection is provided through comparison with previous state.
        
        Returns:
            ButtonState: Complete state with current/previous values and edge detection
        """
        # Read current state from all GPIO pins
        current_state: List[bool] = []
        for pin in self._button_pins:
            # Read GPIO and convert to boolean (HIGH = True, LOW = False)
            gpio_value = GPIO.input(pin)
            button_pressed = (gpio_value == GPIO.HIGH)
            current_state.append(button_pressed)
        
        # Create comprehensive state object 
        # (calculations happen automatically in ButtonState.__post_init__)
        state = ButtonState(
            for_button=current_state,
            previous_state_of=self._previous_state.copy()  # Defensive copy
        )
        
        # Update previous state for next read
        self._previous_state = current_state.copy()
        
        # Log significant changes
        if state.any_changed:
            changed_buttons = [i for i, changed in enumerate(state.was_changed) if changed]
            self._logger.debug(f"Button state changed: buttons {changed_buttons}")
        
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
