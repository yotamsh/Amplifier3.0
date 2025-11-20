"""
Button reader implementation with state management and edge detection
"""

from typing import List

from .interfaces import IButtonReader, IButtonSampler
from .button_state import ButtonState

class ButtonReader(IButtonReader):
    """
    Button reader with state management and edge detection.
    
    Uses IButtonSampler for hardware abstraction (GPIO, keyboard, mock, etc.).
    Manages button state, edge detection, and ignore filtering.
    Follows Dependency Inversion Principle - depends on sampler abstraction.
    
    Example:
        main_logger = HybridLogger("buttons")
        logger = main_logger.get_class_logger("ButtonReader", logging.INFO)
        sampler = GPIOSampler([25, 24, 23], GPIO.PUD_OFF, logger)
        reader = ButtonReader(sampler, logger)
        
        while True:
            state = reader.read_buttons()
            if state.any_changed:
                logger.info(f"Buttons changed: {state}")
    """
    
    def __init__(self, 
                 sampler: IButtonSampler,
                 logger):
        """
        Initialize button reader with injected sampler.
        
        Args:
            sampler: IButtonSampler instance for reading button hardware
            logger: ClassLogger instance from HybridLogger.get_class_logger()
        """
        self._sampler = sampler
        self._logger = logger
        
        # Initialize previous state (all buttons start as not-pressed)
        button_count = sampler.get_button_count()
        self._previous_state: List[bool] = [False] * button_count
        
        # Track buttons to ignore until released
        self._ignored_buttons: List[bool] = [False] * button_count  # True = ignore this button
        
        # Setup sampler hardware
        self._sampler.setup()
        
        self._logger.info(f"ButtonReader initialized with {button_count} buttons")
    
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
        # Read current state from sampler
        for i in range(self._sampler.get_button_count()):
            button_pressed = self._sampler.read_button(i)
            
            if button_pressed:
                self._ignored_buttons[i] = True
                self._previous_state[i] = False  # Prevent false "release" detection
                self._logger.debug(f"Button {i} will be ignored until released")
    
    def read_buttons(self) -> ButtonState:
        """
        Read current state of all buttons with ignore filtering.
        
        Buttons marked as "ignored" will report as not pressed until they are
        physically released, then they return to normal behavior.
        
        Returns:
            ButtonState: Complete state with current/previous values and edge detection
        """
        # Read current state from all buttons via sampler
        raw_current_state: List[bool] = []
        for i in range(self._sampler.get_button_count()):
            button_pressed = self._sampler.read_button(i)
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
        
        # Log each button press (rising edge) individually at INFO level
        # Rising edge: changed AND currently pressed
        for i in range(len(state.for_button)):
            if state.was_changed[i] and state.for_button[i]:
                self._logger.info(f"Button {i} pressed")
        
        # Log each button release (falling edge) individually at DEBUG level
        # Falling edge: changed AND currently NOT pressed
        for i in range(len(state.for_button)):
            if state.was_changed[i] and not state.for_button[i]:
                self._logger.debug(f"Button {i} released")
        
        return state
    
    def get_button_count(self) -> int:
        """Get number of buttons configured in this reader"""
        return self._sampler.get_button_count()
    
    def cleanup(self) -> None:
        """
        Cleanup button reader and sampler resources.
        Automatic cleanup happens via __del__ so this is not required.
        """
        try:
            if hasattr(self, '_sampler'):
                self._sampler.cleanup()
                if hasattr(self, '_logger') and self._logger:
                    self._logger.info("ButtonReader cleaned up successfully")
        except Exception:
            pass  # Silent fail during cleanup
    
    def __del__(self):
        """Automatic cleanup when object is destroyed"""
        self.cleanup()
