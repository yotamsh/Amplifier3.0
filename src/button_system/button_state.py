"""
ButtonState - Immutable button state data with calculated derived fields
"""

from dataclasses import dataclass, field
from typing import List

@dataclass
class ButtonState:
    """
    Immutable snapshot of button states with automatic edge detection.
    
    Usage:
        state = ButtonState([True, False], [False, False])
        print(f"Button 0 changed: {state.was_changed[0]}")
        print(f"Button 0 current: {state.for_button[0]}")
    """
    for_button: List[bool]           # Current state: [button0, button1, ...]
    previous_state_of: List[bool]    # Previous state: [button0_prev, button1_prev, ...]
    
    # Calculated fields (not in constructor, computed automatically)
    was_changed: List[bool] = field(init=False)      # Per-button edge detection
    total_buttons_pressed: int = field(init=False)   # Count of currently pressed buttons
    any_changed: bool = field(init=False)            # True if any button changed state
    
    def __post_init__(self):
        """Calculate derived fields and validate inputs after construction"""
        
        # Input validation
        if not isinstance(self.for_button, list):
            raise TypeError("for_button must be a list of bool")
        if not isinstance(self.previous_state_of, list):
            raise TypeError("previous_state_of must be a list of bool")
        if len(self.for_button) != len(self.previous_state_of):
            raise ValueError(
                f"State lists must have same length: "
                f"for_button={len(self.for_button)}, previous_state_of={len(self.previous_state_of)}"
            )
        
        # Validate all elements are boolean
        if not all(isinstance(x, bool) for x in self.for_button):
            raise TypeError("All elements in for_button must be bool")
        if not all(isinstance(x, bool) for x in self.previous_state_of):
            raise TypeError("All elements in previous_state_of must be bool")
        
        # Calculate edge detection for each button
        self.was_changed = []
        for i in range(len(self.for_button)):
            changed = self.previous_state_of[i] != self.for_button[i]
            self.was_changed.append(changed)
        
        # Calculate aggregate information
        self.total_buttons_pressed = sum(self.for_button)
        self.any_changed = any(self.was_changed)
    
    def get_button_count(self) -> int:
        """Get total number of buttons in this state"""
        return len(self.for_button)
    
    def __str__(self) -> str:
        """Human-readable representation of button state"""
        pressed_buttons = [i for i, pressed in enumerate(self.for_button) if pressed]
        changed_buttons = [i for i, changed in enumerate(self.was_changed) if changed]
        
        return (
            f"ButtonState("
            f"pressed={pressed_buttons}, "
            f"changed={changed_buttons}, "
            f"total_pressed={self.total_buttons_pressed}"
            f")"
        )
