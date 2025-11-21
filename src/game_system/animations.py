"""
Animation base class and concrete implementations for the game system
"""

import math
import random
import time
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, TYPE_CHECKING

from .animation_helpers import AnimationHelpers

if TYPE_CHECKING:
    from led_system.interfaces import LedStrip
    from led_system.pixel import Pixel


class Animation(ABC):
    """
    Abstract base class for time-based animations.
    
    Provides non-blocking, time-based animation updates with configurable speed.
    Each animation operates on a single LED strip.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int):
        """
        Initialize animation with timing control.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Update interval in milliseconds
        """
        self.strip: 'LedStrip' = strip
        self.speed_ms: int = speed_ms
        self.last_update: float = time.time()
    
    def get_name(self) -> str:
        """Get animation name from class name"""
        return self.__class__.__name__
    
    def update_if_needed(self) -> bool:
        """
        Update animation buffer if enough time has passed.
        
        Does NOT call strip.show() - the caller (game state) is responsible
        for calling show() on strips that were updated.
        
        Returns:
            True if strip buffer was modified, False if skipped
        """
        now = time.time()
        elapsed_ms = (now - self.last_update) * 1000
        
        if elapsed_ms >= self.speed_ms:
            self.advance()
            # DON'T call strip.show() - state handles rendering
            self.last_update = now
            return True
        return False
    
    @abstractmethod
    def advance(self) -> None:
        """
        Advance animation by one frame (override in subclasses).
        
        Should update the strip's pixel data but not call show().
        """
        pass


class RainbowAnimation(Animation):
    """
    Continuous rainbow cycle animation.
    
    Creates a flowing rainbow pattern across the entire LED strip
    with configurable speed and hue shifting.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 50, hue_shift_per_frame: int = 8):
        """
        Initialize rainbow animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds  
            hue_shift_per_frame: Degrees to shift hue each frame
        """
        super().__init__(strip, speed_ms)
        self.hue_shift_per_frame: int = hue_shift_per_frame
        self.hue_offset: int = 0
    
    def advance(self) -> None:
        """Advance rainbow hue offset and update strip pixels"""
        self.hue_offset = (self.hue_offset + self.hue_shift_per_frame) % 360
        
        # Update all strip pixels
        num_pixels = self.strip.num_pixels()
        
        for i in range(num_pixels):
            # Calculate hue based on position and offset
            hue = (i * 360 / num_pixels + self.hue_offset) % 360
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
            self.strip[i] = color


class BreathingAnimation(Animation):
    """
    Smooth breathing/pulsing animation with configurable color and brightness range.
    
    Uses sine wave for natural breathing effect across the entire LED strip.
    """
    
    def __init__(self, strip: 'LedStrip', color: 'Pixel', speed_ms: int = 100, 
                 brightness_range: Tuple[float, float] = (0.1, 1.0)):
        """
        Initialize breathing animation.
        
        Args:
            strip: LED strip to operate on
            color: Base color to pulse
            speed_ms: Animation update interval
            brightness_range: (min_brightness, max_brightness) tuple
        """
        super().__init__(strip, speed_ms)
        self.base_color: 'Pixel' = color
        self.brightness_range: Tuple[float, float] = brightness_range
        self.phase: float = 0.0
        self.phase_speed: float = 0.1  # Phase increment per frame (adjust for breathing speed)
    
    def advance(self) -> None:
        """Advance breathing phase and update strip pixels"""
        self.phase += self.phase_speed
        if self.phase > 2 * math.pi:
            self.phase -= 2 * math.pi
        
        # Calculate current brightness using sine wave
        min_brightness, max_brightness = self.brightness_range
        brightness_range = max_brightness - min_brightness
        current_brightness = min_brightness + brightness_range * (0.5 + 0.5 * math.sin(self.phase))
        
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # Create dimmed color
        dimmed_color = Pixel(
            int(self.base_color.r * current_brightness),
            int(self.base_color.g * current_brightness),
            int(self.base_color.b * current_brightness)
        )
        
        # Update entire strip
        self.strip[:] = dimmed_color


class StaticColorAnimation(Animation):
    """
    Simple static color animation for testing and simple effects.
    """
    
    def __init__(self, strip: 'LedStrip', color: 'Pixel'):
        """
        Initialize static color animation.
        
        Args:
            strip: LED strip to operate on
            color: Color to display
        """
        super().__init__(strip, 1000)  # Slow update since it's static
        self.color: 'Pixel' = color
        self._initialized: bool = False
    
    def advance(self) -> None:
        """Set static color once, then no changes needed"""
        if not self._initialized:
            # Update entire strip once
            self.strip[:] = self.color
            self._initialized = True


class IdleAnimation(Animation):
    """
    Dynamic bouncing rainbow scanner animation for idle state.
    
    Creates a single bright LED that bounces back and forth across the strip,
    cycling through rainbow hues with a fading trail effect behind it.
    Based on the classic "Cylon eye" or "scanner" effect.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 50, hue_increment: int = 3, fade_amount: int = 60):
        """
        Initialize idle scanner animation with random starting position and hue.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds
            hue_increment: Amount to increment hue each frame (higher = faster color change)
            fade_amount: Fade strength (0-255, where 255 = fade to target completely, 0 = no fade)
        """
        super().__init__(strip, speed_ms)
        
        # Strip length
        self.num_pixels: int = strip.num_pixels()
        
        # Scanner position and movement - ALWAYS start from random position
        self.led_index: int = random.randint(0, self.num_pixels - 1)
        self.reverse: bool = random.choice([True, False])  # Random initial direction
        
        # Color cycling - ALWAYS start from random hue
        self.hue_index: int = random.randint(0, 359)
        self.hue_increment: int = hue_increment
        
        # Fading effect (increased by 1.5x from 40 to 60)
        self.fade_amount: int = fade_amount
    
    def advance(self) -> None:
        """Advance scanner position (2 pixels together), update colors, and apply fading effect"""
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # 1. Fade all existing pixels using HSV to preserve color (trail effect)
        AnimationHelpers.fade_to_black_hsv(self.strip, self.fade_amount)
        
        # 2. Set current 2 LEDs to bright rainbow color (snake of 2 pixels)
        current_color = AnimationHelpers.hsv_to_pixel(self.hue_index % 360, 1.0, 1.0)
        self.strip[self.led_index] = current_color
        
        # Light the adjacent pixel too (in direction of movement)
        if self.reverse:
            adjacent_index = self.led_index - 1
        else:
            adjacent_index = self.led_index + 1
        
        # Only light adjacent if within bounds
        if 0 <= adjacent_index < self.num_pixels:
            self.strip[adjacent_index] = current_color
        
        # 3. Move LED index by 2 (bouncing motion with 2-pixel step)
        if self.reverse:
            self.led_index -= 2
        else:
            self.led_index += 2
        
        # 4. Reverse direction at strip ends (with 2-pixel snake consideration)
        if self.led_index >= self.num_pixels - 1 or self.led_index <= 0:
            self.reverse = not self.reverse
            # Ensure we stay within bounds
            self.led_index = max(0, min(self.led_index, self.num_pixels - 1))
        
        # 5. Increment hue for next frame (rainbow cycling)
        self.hue_index += self.hue_increment


class HueShiftSnakeAnimation(Animation):
    """
    Snake animation where the head maintains its color and trail pixels shift their hue.
    
    Unlike IdleAnimation which fades pixels but keeps their hue, this animation
    shifts the hue of trail pixels (+10 degrees) creating a color-morphing snake effect.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 25, hue_shift: int = 10, fade_amount: int = 60):
        """
        Initialize hue-shifting snake animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds
            hue_shift: Amount to shift hue of trail pixels each frame (degrees)
            fade_amount: Fade strength for tail (0-255, where 255 = fade completely)
        """
        super().__init__(strip, speed_ms)
        
        # Strip length
        self.num_pixels: int = strip.num_pixels()
        
        # Snake position and movement - start from random position
        self.led_index: int = random.randint(0, self.num_pixels - 1)
        self.reverse: bool = random.choice([True, False])
        
        # Snake color - start from random hue
        self.snake_hue: int = random.randint(0, 359)
        self.hue_shift: int = hue_shift
        
        # Fading effect for tail end
        self.fade_amount: int = fade_amount
    
    def advance(self) -> None:
        """Advance snake position with hue-shifting trail"""
        from led_system.pixel import Pixel
        
        # 1. Shift hue of all existing pixels relative to their previous frame hue
        for i in range(self.num_pixels):
            pixel = self.strip[i]
            
            # Convert pixel to HSV (get pixel's current hue from previous frame)
            h, s, v = AnimationHelpers._rgb_to_hsv(pixel.r, pixel.g, pixel.b)
            
            # Only process pixels that are lit (have brightness > 0)
            if v > 0:
                # Shift hue forward relative to previous frame (hue += self.hue_shift)
                new_hue = (h + self.hue_shift) % 360
                
                # Also fade brightness slightly for tail effect
                new_v = max(0, v - (self.fade_amount / 255.0) * 0.15)  # Gentle fade
                
                # Convert back to RGB
                new_pixel = AnimationHelpers.hsv_to_pixel(new_hue, s, new_v)
                self.strip[i] = new_pixel
        
        # 2. Set current position (2 pixels) to snake's color
        snake_color = AnimationHelpers.hsv_to_pixel(self.snake_hue % 360, 1.0, 1.0)
        self.strip[self.led_index] = snake_color
        
        # Light the adjacent pixel in direction of movement
        if self.reverse:
            adjacent_index = self.led_index - 1
        else:
            adjacent_index = self.led_index + 1
        
        if 0 <= adjacent_index < self.num_pixels:
            self.strip[adjacent_index] = snake_color
        
        # 3. Move LED index by 2 pixels
        if self.reverse:
            self.led_index -= 2
        else:
            self.led_index += 2
        
        # 4. Reverse direction at strip ends
        if self.led_index >= self.num_pixels - 1 or self.led_index <= 0:
            self.reverse = not self.reverse
            # Ensure we stay within bounds
            self.led_index = max(0, min(self.led_index, self.num_pixels - 1))
        
        # 5. Shift snake head hue backward by 3 degrees for next frame
        self.snake_hue = (self.snake_hue - 3) % 360


class AnimationDelayWrapper(Animation):
    """
    Generic wrapper that adds a delay before starting a target animation.
    
    During the delay period, keeps the LED strip black. After the delay,
    delegates all animation behavior to the wrapped target animation.
    """
    
    def __init__(self, target_animation: 'Animation', delay_ms: int):
        """
        Initialize delay wrapper.
        
        Args:
            target_animation: Animation to run after delay
            delay_ms: Delay duration in milliseconds before starting target animation
        """
        super().__init__(target_animation.strip, target_animation.speed_ms)
        self.target_animation: 'Animation' = target_animation
        self.delay_ms: int = delay_ms
        self.start_time: float = time.time() * 1000  # Current time in milliseconds
        self.delay_finished: bool = False
    
    def advance(self) -> None:
        """Either maintain black strip during delay or delegate to target animation"""
        if not self.delay_finished:
            # Check if delay period is over
            current_time = time.time() * 1000
            if current_time - self.start_time >= self.delay_ms:
                self.delay_finished = True
                # Delay finished, start delegating to target animation
                self.target_animation.advance()
            else:
                # Still in delay - keep strip black
                # Import here to avoid circular imports
                from led_system.pixel import Pixel
                black = Pixel(0, 0, 0)
                self.strip[:] = black
        else:
            # Delay finished - delegate to target animation
            self.target_animation.advance()


class AmplifySnakeAnimation(Animation):
    """
    Snake animation that travels only through pressed button segments.
    
    A snake moves back and forth through active segments, leaving permanent
    rainbow colors behind. All active segment pixels shift hue together.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, speed_ms: int = 25):
        """
        Initialize amplify snake animation.
        
        Args:
            strip: LED strip to operate on
            button_count: Number of buttons that control segments
            speed_ms: Animation update interval in milliseconds
        """
        super().__init__(strip, speed_ms)
        self.button_count: int = button_count
        self.leds_per_button: int = strip.num_pixels() // button_count
        self.num_pixels: int = strip.num_pixels()
        
        # Track which buttons are currently pressed
        self.pressed_buttons: List[bool] = [False] * button_count
        self.last_pressed_button: Optional[int] = None
        
        # Snake state
        self.snake_position: int = 0
        self.snake_hue: int = random.randint(0, 359)
        self.snake_direction: int = random.choice([1, -1])  # 1=forward, -1=backward
        self.hue_increment: int = 5  # Hue change per snake movement
        self.snake_speed: int = 2  # Pixels to advance per frame
        self.initialized: bool = False
        
    def set_pressed_buttons(self, pressed_buttons: List[bool]) -> None:
        """Update which buttons are currently pressed."""
        old_pressed = self.pressed_buttons.copy()
        self.pressed_buttons = pressed_buttons.copy()
        
        # Track last pressed button (find newly pressed or rightmost pressed)
        for i in range(self.button_count - 1, -1, -1):
            if pressed_buttons[i] and not old_pressed[i]:
                self.last_pressed_button = i
                self.initialized = False  # Reset snake position
                # Note: Will fill segment with matching colors in advance() after snake direction is set
                break
        
        # If no new press, use rightmost pressed button
        if self.last_pressed_button is None or not pressed_buttons[self.last_pressed_button]:
            for i in range(self.button_count - 1, -1, -1):
                if pressed_buttons[i]:
                    self.last_pressed_button = i
                    break
    
    def _fill_segment_with_snake_trail(self, button_index: int, center_pos: int, direction: int) -> None:
        """Fill a segment with colors matching the snake's trail in opposite direction."""
        segment_start = button_index * self.leds_per_button
        segment_end = (button_index + 1) * self.leds_per_button
        
        # Fill opposite direction from snake movement with matching hues
        if direction > 0:
            # Snake going right, fill left side
            pixels_to_fill = center_pos - segment_start
            for offset in range(1, pixels_to_fill + 1):
                pixel_idx = center_pos - offset
                if segment_start <= pixel_idx < segment_end:
                    # Hue decreases going backwards (opposite of snake's increment)
                    hue = (self.snake_hue - offset * self.hue_increment * self.snake_speed) % 360
                    color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
                    self.strip[pixel_idx] = color
        else:
            # Snake going left, fill right side
            pixels_to_fill = segment_end - center_pos - 1
            for offset in range(1, pixels_to_fill + 1):
                pixel_idx = center_pos + offset
                if segment_start <= pixel_idx < segment_end:
                    # Hue decreases going backwards (opposite of snake's increment)
                    hue = (self.snake_hue - offset * self.hue_increment * self.snake_speed) % 360
                    color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
                    self.strip[pixel_idx] = color
    
    def _get_button_center_pixel(self, button_index: int) -> int:
        """Get the center pixel index for a button segment."""
        center = int(self.num_pixels / self.button_count * (button_index + 0.5) - 1)
        return max(0, min(center, self.num_pixels - 1))
    
    def _get_active_segments(self) -> List[Tuple[int, int]]:
        """Get list of all active segment ranges as (start, end) tuples."""
        active_segments = []
        for button_idx in range(self.button_count):
            if self.pressed_buttons[button_idx]:
                segment_start = button_idx * self.leds_per_button
                segment_end = (button_idx + 1) * self.leds_per_button - 1
                active_segments.append((segment_start, segment_end))
        return active_segments
    
    def _get_current_segment(self, position: int, segments: List[Tuple[int, int]]) -> Optional[int]:
        """Find which segment index the position is in."""
        for i, (start, end) in enumerate(segments):
            if start <= position <= end:
                return i
        return None
    
    def _find_next_segment(self, current_seg_idx: int, segments: List[Tuple[int, int]], direction: int) -> Optional[int]:
        """Find the next active segment in the given direction."""
        if direction > 0:  # Forward
            if current_seg_idx + 1 < len(segments):
                return current_seg_idx + 1
        else:  # Backward
            if current_seg_idx - 1 >= 0:
                return current_seg_idx - 1
        return None
    
    def advance(self) -> None:
        """Advance snake position and update strip pixels"""
        from led_system.pixel import Pixel
        
        # 1. Fade inactive segments to black
        for i in range(self.num_pixels):
            button_idx = i // self.leds_per_button
            if button_idx >= self.button_count or not self.pressed_buttons[button_idx]:
                # Fade inactive segments
                pixel = self.strip[i]
                h, s, v = AnimationHelpers._rgb_to_hsv(pixel.r, pixel.g, pixel.b)
                if v > 0:
                    new_v = max(0, v - 0.15)  # Fade brightness
                    self.strip[i] = AnimationHelpers.hsv_to_pixel(h, s, new_v)
        
        # Get list of active segments
        active_segments = self._get_active_segments()
        
        if not active_segments:
            # No active segments - show only blinking dots
            beat_value = AnimationHelpers.beat8(40)
            for button_index in range(self.button_count):
                if not self.pressed_buttons[button_index]:
                    center_pixel = self._get_button_center_pixel(button_index)
                    if beat_value > 240:
                        self.strip[center_pixel] = AnimationHelpers.ORANGE_RED
                    else:
                        self.strip[center_pixel] = AnimationHelpers.BLACK
            return
        
        # Initialize snake position if needed
        if not self.initialized and self.last_pressed_button is not None:
            self.snake_position = self._get_button_center_pixel(self.last_pressed_button)
            self.snake_direction = random.choice([1, -1])
            # Fill the opposite direction with matching trail colors
            self._fill_segment_with_snake_trail(self.last_pressed_button, self.snake_position, self.snake_direction)
            self.initialized = True
        
        # 2. Move snake with segment skipping (faster movement)
        current_seg_idx = self._get_current_segment(self.snake_position, active_segments)
        
        if current_seg_idx is not None:
            current_seg_start, current_seg_end = active_segments[current_seg_idx]
            next_pos = self.snake_position + (self.snake_direction * self.snake_speed)
            
            # Check if we've reached the boundary of current segment
            if self.snake_direction > 0 and next_pos > current_seg_end:
                # Moving forward, reached end of segment
                next_seg_idx = self._find_next_segment(current_seg_idx, active_segments, 1)
                if next_seg_idx is not None:
                    # Jump to start of next segment
                    overshoot = next_pos - current_seg_end - 1
                    next_pos = active_segments[next_seg_idx][0] + overshoot
                else:
                    # No more segments forward - reverse direction
                    self.snake_direction = -1
                    next_pos = current_seg_end + (next_pos - current_seg_end) * self.snake_direction
                    next_pos = max(current_seg_start, min(next_pos, current_seg_end))
            
            elif self.snake_direction < 0 and next_pos < current_seg_start:
                # Moving backward, reached start of segment
                next_seg_idx = self._find_next_segment(current_seg_idx, active_segments, -1)
                if next_seg_idx is not None:
                    # Jump to end of previous segment
                    undershoot = current_seg_start - next_pos - 1
                    next_pos = active_segments[next_seg_idx][1] - undershoot
                else:
                    # No more segments backward - reverse direction
                    self.snake_direction = 1
                    next_pos = current_seg_start + (current_seg_start - next_pos) * self.snake_direction
                    next_pos = max(current_seg_start, min(next_pos, current_seg_end))
            
            self.snake_position = next_pos
        
        # 3. Paint snake head (wider for faster movement) - permanent color
        snake_color = AnimationHelpers.hsv_to_pixel(self.snake_hue % 360, 1.0, 1.0)
        
        # Paint wider head to cover the speed (snake_speed * 2 + 1 pixels)
        head_width = self.snake_speed + 1
        for offset in range(-head_width, head_width + 1):
            pixel_idx = self.snake_position + offset
            if 0 <= pixel_idx < self.num_pixels:
                button_idx = pixel_idx // self.leds_per_button
                if button_idx < self.button_count and self.pressed_buttons[button_idx]:
                    self.strip[pixel_idx] = snake_color
        
        # Increment snake hue for next movement (proportional to speed)
        self.snake_hue = (self.snake_hue + self.hue_increment * self.snake_speed) % 360
        
        # 4. Add blinking OrangeRed indicators on unpressed button centers
        beat_value = AnimationHelpers.beat8(40)
        for button_index in range(self.button_count):
            if not self.pressed_buttons[button_index]:
                center_pixel = self._get_button_center_pixel(button_index)
                if beat_value > 240:
                    self.strip[center_pixel] = AnimationHelpers.ORANGE_RED
                else:
                    self.strip[center_pixel] = AnimationHelpers.BLACK


class AmplifyAnimation(Animation):
    """
    Rainbow animation that only illuminates LED segments corresponding to pressed buttons.
    
    Each button controls a segment of the LED strip. Only pressed button segments
    show the rainbow pattern, while unpressed segments have a blinking OrangeRed indicator.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, speed_ms: int = 100, 
                 hue_shift_per_frame: int = 10):
        """
        Initialize amplify animation.
        
        Args:
            strip: LED strip to operate on
            button_count: Number of buttons that control segments
            speed_ms: Animation update interval in milliseconds (higher = slower)
            hue_shift_per_frame: Degrees to shift hue each frame (higher = faster)
        """
        super().__init__(strip, speed_ms)
        self.button_count: int = button_count
        self.hue_shift_per_frame: int = hue_shift_per_frame
        self.hue_offset: int = 0
        self.hue_spread: float = 6.7  # Higher value = more color variation between pixels (1/3 more dense)
        
        # Calculate LEDs per button (constant for this animation instance)
        self.leds_per_button: int = strip.num_pixels() // button_count
        
        # Track which buttons are currently pressed
        self.pressed_buttons: List[bool] = [False] * button_count
        
    
    def set_pressed_buttons(self, pressed_buttons: List[bool]) -> None:
        """
        Update which buttons are currently pressed.
        
        Args:
            pressed_buttons: List of boolean values indicating button press state
        """
        self.pressed_buttons = pressed_buttons.copy()
    
    def _get_button_center_pixel(self, button_index: int) -> int:
        """
        Get the center pixel index for a button segment.
        
        Formula: totalLeds/buttonsCount*(button_index+0.5)-1
        
        Args:
            button_index: Index of the button (0-based)
            
        Returns:
            Center pixel index for that button's segment
        """
        num_pixels = self.strip.num_pixels()
        center = int(num_pixels / self.button_count * (button_index + 0.5) - 1)
        return max(0, min(center, num_pixels - 1))  # Clamp to valid range
    
    def advance(self) -> None:
        """Advance rainbow hue offset and update strip pixels based button state"""
        self.hue_offset = (self.hue_offset + self.hue_shift_per_frame) % 360
        
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # 1. First, apply HSV fading to create trails for released button segments
        AnimationHelpers.fade_to_black_hsv(self.strip, fade_amount=60, min_brightness=0.0)
        
        # 2. Update all strip pixels based on current button state
        num_pixels = self.strip.num_pixels()
        
        for led_pos in range(num_pixels):
            # Calculate which button segment this LED belongs to
            button_index = led_pos // self.leds_per_button
            
            # Check if this button is pressed (with bounds checking)
            if button_index < self.button_count and self.pressed_buttons[button_index]:
                # Calculate rainbow hue with higher spread between pixels
                hue = (led_pos * self.hue_spread + self.hue_offset) % 360
                color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
                self.strip[led_pos] = color
            # Note: No explicit "else" - let fading handle unpressed segments
        
        # 3. Add blinking OrangeRed indicators on unpressed button centers
        # Using beat8-style blinking: on when beat > 240 (short blink every ~1.5 seconds)
        beat_value = AnimationHelpers.beat8(40)  # 40 BPM = blink every 1.5 seconds (double speed)
        
        for button_index in range(self.button_count):
            if not self.pressed_buttons[button_index]:
                center_pixel = self._get_button_center_pixel(button_index)
                if beat_value > 240:
                    # Blink on - show OrangeRed
                    self.strip[center_pixel] = AnimationHelpers.ORANGE_RED
                else:
                    # Blink off - force to black (override fade)
                    self.strip[center_pixel] = AnimationHelpers.BLACK


class AmplifyPyramidAnimation(Animation):
    """
    Pyramid fill animation based on number of pressed buttons.
    
    Fills the pyramid from bottom to top proportionally to the number
    of pressed buttons. Uses PyramidMapping for height-based control.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, speed_ms: int = 50):
        """
        Initialize pyramid amplify animation.
        
        Args:
            strip: LED strip to operate on (pyramid strip)
            button_count: Total number of buttons in the system
            speed_ms: Animation update interval in milliseconds
        """
        super().__init__(strip, speed_ms)
        self.button_count: int = button_count
        
        # Track which buttons are currently pressed
        self.pressed_buttons: List[bool] = [False] * button_count
        
        # Fill color - white
        from led_system.pixel import Pixel
        self.fill_color = Pixel(255, 255, 255)
        self.off_color = Pixel(0, 0, 0)
    
    def set_pressed_buttons(self, pressed_buttons: List[bool]) -> None:
        """
        Update which buttons are currently pressed.
        
        Args:
            pressed_buttons: List of boolean values indicating button press state
        """
        self.pressed_buttons = pressed_buttons.copy()
    
    def advance(self) -> None:
        """Update pyramid LEDs based on number of pressed buttons with analog noise"""
        from game_system.animation_helpers import pyramidHeight
        import random
        
        # Count how many buttons are pressed
        buttons_pressed = sum(self.pressed_buttons)
        
        # Calculate base fill percentage: (buttons_pressed / total_buttons) * 100
        base_fill_percent = int((buttons_pressed / self.button_count) * 100)
        
        # Add analog noise: ±2 heights for organic feel
        noise = random.randint(-2, 2)
        fill_percent = base_fill_percent + noise
        
        # Clamp to valid range (0-100)
        fill_percent = max(0, min(100, fill_percent))
        
        # Get LEDs to light (from bottom to fill_percent height)
        leds_to_light = pyramidHeight[0:fill_percent]
        
        # Clear entire strip first
        num_pixels = self.strip.num_pixels()
        for i in range(num_pixels):
            self.strip[i] = self.off_color
        
        # Light the bottom portion
        for led_idx in leds_to_light:
            self.strip[led_idx] = self.fill_color


class SequenceAnimation(Animation):
    """
    Composite animation that plays child animations in sequence.
    
    Each animation in the sequence plays for a specified duration,
    then transitions to the next. Can optionally loop back to start.
    
    Args:
        strip: LED strip to operate on
        animation_sequence: List of (Animation, duration_seconds) tuples.
                           Duration can be None for last item (plays forever).
        repeat: If True, loops back to first animation after sequence ends.
        frame_speed_ms: How often to check for phase switches (typically 20ms).
    
    Example:
        seq = SequenceAnimation(
            strip=strip,
            animation_sequence=[
                (BlinkAnimation(strip), 5.0),    # 5 seconds
                (RainbowAnimation(strip), 10.0), # 10 seconds
                (WaveAnimation(strip), None)     # Forever
            ],
            repeat=False,
            frame_speed_ms=20
        )
    """
    
    def __init__(self, strip: 'LedStrip', 
                 animation_sequence: List[Tuple['Animation', Optional[float]]],
                 repeat: bool = False,
                 frame_speed_ms: int = 20):
        super().__init__(strip, frame_speed_ms)
        self.sequence = animation_sequence
        self.repeat = repeat
        self.current_index = 0
        self.phase_start_time = time.time()
        
        if animation_sequence:
            self.current_animation = animation_sequence[0][0]
        else:
            self.current_animation = None
    
    def advance(self) -> None:
        """Check for phase switches, then delegate to current child animation"""
        current_time = time.time()
        
        # Check if should advance to next animation
        if self.current_index < len(self.sequence):
            _, duration = self.sequence[self.current_index]
            
            if duration is not None:
                if current_time - self.phase_start_time >= duration:
                    # Time to switch to next animation
                    self.current_index += 1
                    
                    if self.current_index >= len(self.sequence):
                        if self.repeat:
                            # Loop back to start
                            self.current_index = 0
                        else:
                            # Stay on last
                            self.current_index = len(self.sequence) - 1
                    
                    self.current_animation = self.sequence[self.current_index][0]
                    self.phase_start_time = current_time
        
        # Delegate rendering to current child
        # Child checks its own timing and updates if needed
        if self.current_animation:
            self.current_animation.update_if_needed()
    
    def update_if_needed(self) -> bool:
        """
        Override to prevent double strip.show().
        Child's update_if_needed() already calls show().
        """
        now = time.time()
        elapsed_ms = (now - self.last_update) * 1000
        
        if elapsed_ms >= self.speed_ms:
            self.advance()
            # DON'T call strip.show() - child already did it
            self.last_update = now
            return True
        return False


class BlinkPyramidAnimation(Animation):
    """Pyramid blink animation - toggle between vibrant colors and black"""
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 50):
        super().__init__(strip, speed_ms)
        
        from led_system.pixel import Pixel
        self.current_color = Pixel(255, 255, 255)  # Start with white
        self.is_lit = True
        self.is_first_blink = True
        self.blink_interval_ms = 400  # 400ms per on/off toggle
        self.last_blink_time = time.time()
        self.black = Pixel(0, 0, 0)
    
    def _get_random_vibrant_color(self) -> 'Pixel':
        """Generate a random vibrant, pleasant color"""
        from led_system.pixel import Pixel
        
        colors = [
            Pixel(255, 105, 180),  # Hot pink
            Pixel(100, 149, 237),  # Cornflower blue
            Pixel(144, 238, 144),  # Light green
            Pixel(255, 165, 0),    # Orange
            Pixel(186, 85, 211),   # Medium orchid
            Pixel(255, 215, 0),    # Gold
            Pixel(64, 224, 208),   # Turquoise
            Pixel(255, 20, 147),   # Deep pink
            Pixel(30, 144, 255),   # Dodger blue
            Pixel(255, 99, 71),    # Tomato red
            Pixel(147, 112, 219),  # Medium purple
            Pixel(50, 205, 50),    # Lime green
        ]
        return random.choice(colors)
    
    def advance(self) -> None:
        """Toggle pyramid on/off, changing color when turning on"""
        current_time = time.time()
        elapsed_ms = (current_time - self.last_blink_time) * 1000
        
        # Check if it's time to toggle
        if elapsed_ms >= self.blink_interval_ms:
            self.is_lit = not self.is_lit
            
            # When turning on, pick a new color
            if self.is_lit:
                if self.is_first_blink:
                    self.is_first_blink = False
                else:
                    self.current_color = self._get_random_vibrant_color()
            
            self.last_blink_time = current_time
        
        # Fill pyramid with current state (lit color or black)
        num_pixels = self.strip.num_pixels()
        display_color = self.current_color if self.is_lit else self.black
        
        for i in range(num_pixels):
            self.strip[i] = display_color


class RainbowWavePyramidAnimation(Animation):
    """Rainbow wave animation - dense rainbow with complex sin-based movement"""
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 50):
        super().__init__(strip, speed_ms)
    
    def advance(self) -> None:
        """Render rainbow wave with sin-based hue offset"""
        from game_system.animation_helpers import AnimationHelpers
        
        # Complex hue offset using combination of three sin waves
        sin_a = AnimationHelpers.sin8(0.07)  # Slow wave
        sin_b = AnimationHelpers.sin8(0.19)  # Medium wave
        sin_c = AnimationHelpers.sin8(0.53)  # Fast wave
        
        # Combine and scale (3x speed multiplier)
        hue_offset = (sin_a + sin_b + sin_c) * 360 / (255 * 3) * 3
        
        num_pixels = self.strip.num_pixels()
        
        # Apply dense rainbow gradient
        for i in range(num_pixels):
            hue = (i * 3 + hue_offset) % 360
            color = AnimationHelpers.hsv_to_pixel(hue, 0.9, 1.0)
            self.strip[i] = color


class PermutationColorsPyramidAnimation(Animation):
    """Permutation color change - colors change pixel by pixel in permutation order"""
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 20):
        super().__init__(strip, speed_ms)
        
        self.perm_prev_color = None
        self.perm_new_color = None
        self.perm_pixel_index = 0
    
    def advance(self) -> None:
        """Change 2 pixels per advance in permutation order"""
        from game_system.animation_helpers import AnimationHelpers, STRIP_PERMUTATIONS
        
        # Strip 1 (pyramid) uses index 1
        strip_index = 1
        
        if strip_index not in STRIP_PERMUTATIONS:
            return
        
        permutation = STRIP_PERMUTATIONS[strip_index]
        
        # Initialize colors if first time
        if self.perm_prev_color is None:
            random_hue = random.random() * 360
            self.perm_prev_color = AnimationHelpers.hsv_to_pixel(random_hue, 1.0, 1.0)
            
            # Fill entire strip
            for i in range(self.strip.num_pixels()):
                self.strip[i] = self.perm_prev_color
            
            # Pick new color
            random_hue = random.random() * 360
            self.perm_new_color = AnimationHelpers.hsv_to_pixel(random_hue, 1.0, 1.0)
            self.perm_pixel_index = 0
        
        # Change 2 pixels per advance call
        pixels_to_change = 2
        for _ in range(pixels_to_change):
            if self.perm_pixel_index < len(permutation):
                pixel_to_change = permutation[self.perm_pixel_index]
                self.strip[pixel_to_change] = self.perm_new_color
                self.perm_pixel_index += 1
            else:
                # All pixels changed - restart with new colors
                self.perm_prev_color = self.perm_new_color
                random_hue = random.random() * 360
                self.perm_new_color = AnimationHelpers.hsv_to_pixel(random_hue, 1.0, 1.0)
                self.perm_pixel_index = 0
                break  # Start fresh next advance call


class PyramidMusicBarAnimation(Animation):
    """
    Music bar visualization - entire pyramid fills from bottom with white light.
    
    Simulates realistic music amplitude with smooth beat and analog noise.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 25):
        super().__init__(strip, speed_ms)
    
    def _calculate_current_height(self) -> int:
        """
        Calculate current fill height (0-100) simulating realistic music amplitude.
        
        Smooth, rhythmic beat with analog noise - emphasis on beat feeling.
        """
        from game_system.animation_helpers import AnimationHelpers
        import random
        
        # === 140 BPM BASE BEAT (primary rhythm) ===
        # Slightly slower for more dramatic, smooth pulses
        # 140 BPM = 2.33 Hz
        beat_raw = AnimationHelpers.sin8(2.33) / 255.0
        # Power of 3 for smooth but pronounced beat
        base_beat = beat_raw ** 3  # Strong but smooth
        
        # === SUB-BASS (half tempo) ===
        # 70 BPM = 1.17 Hz - slower depth layer
        sub_bass_raw = AnimationHelpers.sin8(1.17, 45) / 255.0
        sub_bass = sub_bass_raw ** 2  # Gentle, rolling bass
        
        # === MELODIC WAVE (slower movement) ===
        # Simulates melody/bassline - 35 BPM = 0.58 Hz
        melodic = AnimationHelpers.sin8(0.58, 180) / 255.0
        # No power - pure smooth sine
        
        # === COMBINE LAYERS (weighted mix, emphasis on beat) ===
        combined = (
            base_beat * 0.55 +      # Main beat (55% - more prominent)
            sub_bass * 0.25 +       # Sub-bass depth (25%)
            melodic * 0.20          # Melodic content (20%)
        )
        
        # Clamp to 0-1 range
        combined = max(0.0, min(1.0, combined))
        
        # === DYNAMIC RANGE COMPRESSION (emphasize rhythm) ===
        # Gentler compression for more natural flow
        compressed = combined ** 0.85  # Lighter compression
        
        # Scale to 10-90 range
        base_height = int(10 + compressed * 80)
        
        # === ANALOG NOISE (±2 height random variation) ===
        noise = random.randint(-2, 2)
        height = base_height + noise
        
        return max(10, min(100, height))
    
    def advance(self) -> None:
        """Fill pyramid from bottom to current height with white light"""
        from game_system.animation_helpers import pyramidHeight
        from led_system.pixel import Pixel
        
        white = Pixel(255, 255, 255)
        black = Pixel(0, 0, 0)
        
        # Calculate current height
        current_height = self._calculate_current_height()
        
        # Get all pixels below current height
        lit_pixels = pyramidHeight[0:current_height]
        
        # Clear entire strip first
        num_pixels = self.strip.num_pixels()
        for i in range(num_pixels):
            if i in lit_pixels:
                self.strip[i] = white
            else:
                self.strip[i] = black


class PyramidVerticalColorWipe(Animation):
    """
    Vertical color wipe animation - fills pyramid with solid colors from bottom-up, then top-down.
    
    Wipes alternate directions: bottom→top, top→bottom, repeat.
    Each wipe uses a new hue (incremented by constant amount).
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 20, hue_increment: int = 46):
        super().__init__(strip, speed_ms)
        
        self.current_hue = 0  # Starting hue (0-360)
        self.hue_increment = hue_increment  # Hue change per wipe
        self.wipe_direction = 'up'  # 'up' or 'down'
        self.wipe_progress = 0  # Current height of wipe (0-100)
        self.wipe_speed = 4  # Height units to advance per frame
        
        # Initialize strip with starting color
        from game_system.animation_helpers import AnimationHelpers, pyramidHeight
        from led_system.pixel import Pixel
        
        start_color = AnimationHelpers.hsv_to_pixel(self.current_hue, 1.0, 1.0)
        for i in range(strip.num_pixels()):
            strip[i] = start_color
    
    def advance(self) -> None:
        """Advance wipe animation - fill pyramid progressively with new color"""
        from game_system.animation_helpers import AnimationHelpers, pyramidHeight
        
        # Advance wipe progress
        self.wipe_progress += self.wipe_speed
        
        # Calculate colors
        old_hue = (self.current_hue - self.hue_increment) % 360
        new_hue = self.current_hue
        
        old_color = AnimationHelpers.hsv_to_pixel(old_hue, 1.0, 1.0)
        new_color = AnimationHelpers.hsv_to_pixel(new_hue, 1.0, 1.0)
        
        if self.wipe_direction == 'up':
            # Wipe from bottom to top
            if self.wipe_progress <= 100:
                # Fill bottom part with new color, top part with old color
                lit_pixels = pyramidHeight[0:self.wipe_progress]
                remaining_pixels = pyramidHeight[self.wipe_progress:100] if self.wipe_progress < 100 else set()
                
                for i in range(self.strip.num_pixels()):
                    if i in lit_pixels:
                        self.strip[i] = new_color
                    elif i in remaining_pixels:
                        self.strip[i] = old_color
            else:
                # Wipe complete - switch direction and increment hue
                self.wipe_direction = 'down'
                self.wipe_progress = 0
                self.current_hue = (self.current_hue + self.hue_increment) % 360
        
        else:  # wipe_direction == 'down'
            # Wipe from top to bottom
            if self.wipe_progress <= 100:
                # Fill top part with new color, bottom part with old color
                start_height = 100 - self.wipe_progress
                lit_pixels = pyramidHeight[start_height:100] if start_height >= 0 else pyramidHeight[0:100]
                remaining_pixels = pyramidHeight[0:start_height] if start_height > 0 else set()
                
                for i in range(self.strip.num_pixels()):
                    if i in lit_pixels:
                        self.strip[i] = new_color
                    elif i in remaining_pixels:
                        self.strip[i] = old_color
            else:
                # Wipe complete - switch direction and increment hue
                self.wipe_direction = 'up'
                self.wipe_progress = 0
                self.current_hue = (self.current_hue + self.hue_increment) % 360


class CodeModePyramidAnimation(Animation):
    """
    Code mode pyramid animation - lights up pixels in permutation order with blue gradient.
    
    Phase 1: Light up pixels one by one (permutation order) with blue gradient
    Phase 2: Turn off pixels one by one (same permutation order)
    Repeat.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 20):
        super().__init__(strip, speed_ms)
        
        self.phase = 'lighting'  # 'lighting' or 'clearing'
        self.pixel_index = 0
        self.num_pixels = strip.num_pixels()
        
        # Pre-calculate blue gradient for each pixel (based on pixel index)
        # Darker blue (hue=240, low value) → Lighter blue (hue=200, high value)
        from game_system.animation_helpers import AnimationHelpers
        self.pixel_colors = []
        for i in range(self.num_pixels):
            progress = i / max(1, self.num_pixels - 1)
            # Hue: 240 (pure blue) → 200 (cyan-blue)
            hue = 240 - (progress * 40)
            # Value: 0.4 → 1.0 (darker → lighter)
            value = 0.4 + (progress * 0.6)
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, value)
            self.pixel_colors.append(color)
        
        # Start with all black
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for i in range(self.num_pixels):
            strip[i] = black
    
    def advance(self) -> None:
        """Light or clear 2 pixels per advance in permutation order"""
        from game_system.animation_helpers import STRIP_PERMUTATIONS
        from led_system.pixel import Pixel
        
        # Strip 1 (pyramid) uses index 1
        strip_index = 1
        
        if strip_index not in STRIP_PERMUTATIONS:
            return
        
        permutation = STRIP_PERMUTATIONS[strip_index]
        black = Pixel(0, 0, 0)
        
        # Process 2 pixels per advance call
        pixels_per_advance = 2
        for _ in range(pixels_per_advance):
            if self.pixel_index < len(permutation):
                pixel_to_modify = permutation[self.pixel_index]
                
                if self.phase == 'lighting':
                    # Light up with gradient color
                    self.strip[pixel_to_modify] = self.pixel_colors[pixel_to_modify]
                else:  # phase == 'clearing'
                    # Turn off
                    self.strip[pixel_to_modify] = black
                
                self.pixel_index += 1
            else:
                # Phase complete - switch phase
                if self.phase == 'lighting':
                    self.phase = 'clearing'
                else:
                    self.phase = 'lighting'
                self.pixel_index = 0
                break  # Start fresh next advance call


class PartyPyramidAnimation(Animation):
    """
    Party pyramid animation with red override support.
    
    Wraps a SequenceAnimation and applies red override (from top down) 
    after the child animation renders.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 20, max_spread: int = None):
        super().__init__(strip, speed_ms)
        
        # Store max_spread for red override calculation
        self.max_spread = max_spread if max_spread else 0
        
        # Red override state
        self.a_red_pixels = 0
        self.b_red_pixels = 0
        
        # Create the child sequence animation (all pyramid animations)
        blink = BlinkPyramidAnimation(strip, speed_ms=50)
        
        random_anims = [
            RainbowWavePyramidAnimation(strip, speed_ms=50),
            PermutationColorsPyramidAnimation(strip, speed_ms=20),
            PyramidMusicBarAnimation(strip, speed_ms=25),
            PyramidVerticalColorWipe(strip, speed_ms=20, hue_increment=46)
        ]
        random.shuffle(random_anims)
        
        random_loop = SequenceAnimation(
            strip=strip,
            animation_sequence=[(a, 20.0) for a in random_anims],
            repeat=True,
            frame_speed_ms=20
        )
        
        self.child_animation = SequenceAnimation(
            strip=strip,
            animation_sequence=[
                (blink, 5.0),
                (random_loop, None)
            ],
            repeat=False,
            frame_speed_ms=20
        )
    
    def set_red_override(self, a_red_pixels: int, b_red_pixels: int) -> None:
        """
        Set red override pixels.
        
        Args:
            a_red_pixels: Number of spread pixels from button A
            b_red_pixels: Number of spread pixels from button B
        """
        self.a_red_pixels = a_red_pixels
        self.b_red_pixels = b_red_pixels
    
    def advance(self) -> None:
        """Render child animation, then apply red override on top"""
        # Let child animation render first
        self.child_animation.update_if_needed()
        
        # Apply red override on top if any buttons held
        if self.a_red_pixels > 0 or self.b_red_pixels > 0:
            self._apply_red_override()
    
    def _apply_red_override(self) -> None:
        """Apply red override from top down based on spread percentage"""
        from game_system.animation_helpers import pyramidHeight
        from led_system.pixel import Pixel
        
        if self.max_spread == 0:
            return  # Avoid division by zero
        
        # Calculate red override percentage
        total_spread = self.a_red_pixels + self.b_red_pixels
        red_override_percent = int(100 * total_spread / (2 * self.max_spread))
        red_override_percent = max(0, min(100, red_override_percent))
        
        # Get pixels to override (from top down)
        # If redOverridePercent is 30%, light red from height 70 to 100
        if red_override_percent > 0:
            start_height = 100 - red_override_percent
            red_pixels = pyramidHeight[start_height:100]
            
            red = Pixel(255, 0, 0)
            for pixel_idx in red_pixels:
                self.strip[pixel_idx] = red


def create_party_pyramid_animation(strip: 'LedStrip', max_spread: int = None) -> PartyPyramidAnimation:
    """
    Factory function to create party pyramid animation with red override support.
    
    Args:
        strip: LED strip to animate (pyramid strip)
        max_spread: Maximum spread value from PartyAnimation (for red override calculation)
        
    Returns:
        PartyPyramidAnimation with red override support
    """
    return PartyPyramidAnimation(strip, speed_ms=20, max_spread=max_spread)


class PushingBandsAnimation(Animation):
    """
    Elegant pushing wave animation - bands emanate from center outward.
    
    Creates color bands that appear in the center and push outward symmetrically.
    New colors enter at the center, pushing previous colors toward the edges.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = None):
        """
        Initialize pushing bands animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds (random if None)
        """
        # Pick random speed if not provided (faster range)
        if speed_ms is None:
            speed_ms = random.randint(10, 20)
        
        super().__init__(strip, speed_ms)
        self.num_pixels: int = strip.num_pixels()
        
        # Determine center position(s)
        # For even pixel count, we have two centers
        self.center1: int = self.num_pixels // 2 - 1
        self.center2: int = self.num_pixels // 2
        self.is_even: bool = (self.num_pixels % 2 == 0)
        
        # Color palette (initialized immediately)
        self.colors = [
            AnimationHelpers.RED_WINE,
            AnimationHelpers.GREEN_GRASS,
            AnimationHelpers.PURPLE,
            AnimationHelpers.SOFT_WHITE
        ]
        
        # Wave state: track position with fixed band width for smooth animation
        self.wave_position: int = 0  # How far the wave has traveled from center
        self.band_width: int = 25  # Fixed width for consistent, smooth bands
        self.speed_change_interval: int = self.band_width * len(self.colors)  # Change speed after full color cycle
    
    def advance(self) -> None:
        """
        Stateless wave effect - calculates each pixel's color independently
        based on distance from center and current wave position.
        """
        # Advance wave position
        self.wave_position += 1
        
        # Optionally vary speed after full color cycle (smooth transitions)
        if self.wave_position % self.speed_change_interval == 0:
            self.speed_ms = random.randint(10, 20)
        
        # Calculate color for each pixel based on distance from center
        for i in range(self.num_pixels):
            # Calculate distance from center
            if self.is_even:
                # Distance from nearest center
                dist = min(abs(i - self.center1), abs(i - self.center2))
            else:
                dist = abs(i - self.center2)
            
            # Determine which color band this pixel is in
            # Subtract wave_position to create outward movement effect
            band_position = (dist - self.wave_position) // self.band_width
            
            # Use modulo to cycle through colors, handle negative with abs
            color_idx = abs(band_position) % len(self.colors)
            self.strip[i] = self.colors[color_idx]


class WinEffectAnimation(Animation):
    """
    Win effect animation - fills rainbow from center of each segment to edges.
    
    All segments fill simultaneously with rainbow gradient (saturation 0.93).
    Creates a dramatic reveal effect from button centers outward.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, speed_ms: int = 50):
        """
        Initialize win effect animation.
        
        Args:
            strip: LED strip to operate on
            button_count: Number of button segments
            speed_ms: Animation update interval in milliseconds
        """
        super().__init__(strip, speed_ms)
        self.button_count: int = button_count
        self.leds_per_button: int = strip.num_pixels() // button_count
        self.num_pixels: int = strip.num_pixels()
        
        # Animation state - tracks how many pixels from center have been revealed
        self.reveal_distance: int = 0  # 0 to leds_per_button/2
        self.max_distance: int = self.leds_per_button // 2
        
        # Start with all black
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for i in range(self.num_pixels):
            strip[i] = black
    
    def advance(self) -> None:
        """Reveal one more pixel distance from each segment center"""
        from game_system.animation_helpers import AnimationHelpers
        
        # Fill all segments from center outward
        for button_idx in range(self.button_count):
            # Calculate segment range
            segment_start = button_idx * self.leds_per_button
            segment_end = (button_idx + 1) * self.leds_per_button
            segment_center = (segment_start + segment_end) // 2
            
            # Calculate rainbow hue for this segment (spread across strip)
            base_hue = (button_idx * 360 / self.button_count) % 360
            
            # Fill pixels at current reveal distance from center
            for offset in range(-self.reveal_distance, self.reveal_distance + 1):
                pixel_idx = segment_center + offset
                
                # Bounds check within segment
                if segment_start <= pixel_idx < segment_end:
                    # Slight hue variation based on distance from segment center
                    hue = (base_hue + abs(offset) * 2) % 360
                    color = AnimationHelpers.hsv_to_pixel(hue, 0.93, 1.0)
                    self.strip[pixel_idx] = color
        
        # Advance reveal distance (stop when full segment is revealed)
        if self.reveal_distance < self.max_distance:
            self.reveal_distance += 1


class RainbowBlinkAnimation(Animation):
    """
    Rainbow blink animation - blinks the current strip pattern several times.
    
    Captures the initial strip state on first advance and alternates between showing it and black.
    """
    
    def __init__(self, strip: 'LedStrip', blink_count: int = 5, speed_ms: int = 200):
        """
        Initialize rainbow blink animation.
        
        Args:
            strip: LED strip to operate on
            blink_count: Number of times to blink (on/off cycles)
            speed_ms: Duration of each blink state (on or off)
        """
        super().__init__(strip, speed_ms)
        self.num_pixels: int = strip.num_pixels()
        self.blink_count: int = blink_count
        
        # Lazy initialization - capture pattern on first advance()
        from led_system.pixel import Pixel
        self.saved_pattern: Optional[List['Pixel']] = None
        self.black = Pixel(0, 0, 0)
        self.blink_state: bool = True  # Start with pattern visible
        self.blinks_completed: int = 0
    
    def advance(self) -> None:
        """Toggle between saved pattern and black"""
        from led_system.pixel import Pixel
        
        # Capture pattern on first call (lazy initialization)
        if self.saved_pattern is None:
            self.saved_pattern = []
            for i in range(self.num_pixels):
                pixel = self.strip[i]
                self.saved_pattern.append(Pixel(pixel.r, pixel.g, pixel.b))
        
        # Toggle blink state
        self.blink_state = not self.blink_state
        
        # Count blinks (one complete blink = on + off)
        if not self.blink_state:
            self.blinks_completed += 1
        
        # Render current state
        if self.blink_state:
            # Show saved pattern
            for i in range(self.num_pixels):
                self.strip[i] = self.saved_pattern[i]
        else:
            # Show black
            for i in range(self.num_pixels):
                self.strip[i] = self.black


class RainbowSinWaveAnimation(Animation):
    """
    Rainbow animation with complex sin-based hue offset.
    
    Uses combination of three sine waves: sin(13) + sin(59) + sin(17)
    Creates an organic, unpredictable color shifting pattern.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 50):
        """
        Initialize rainbow sin wave animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds
        """
        super().__init__(strip, speed_ms)
        self.num_pixels: int = strip.num_pixels()
        self.button_count: int = 10  # Assume 10 segments for rainbow distribution
        self.leds_per_button: int = strip.num_pixels() // self.button_count
    
    def advance(self) -> None:
        """Render rainbow with complex sin-based hue offset"""
        from game_system.animation_helpers import AnimationHelpers
        
        # Calculate complex hue offset using three sin waves
        sin_13 = AnimationHelpers.sin8(13 / 60.0)  # Slow wave (13 BPM = 0.217 Hz)
        sin_59 = AnimationHelpers.sin8(59 / 60.0)  # Medium wave (59 BPM = 0.983 Hz)
        sin_17 = AnimationHelpers.sin8(17 / 60.0)  # Medium-slow wave (17 BPM = 0.283 Hz)
        
        # Combine and scale to hue degrees (0-360)
        hue_offset = (sin_13 + sin_59 + sin_17) * 360 / (255 * 3)
        
        # Render rainbow across segments
        for button_idx in range(self.button_count):
            segment_start = button_idx * self.leds_per_button
            segment_end = min((button_idx + 1) * self.leds_per_button, self.num_pixels)
            
            # Base hue for this segment
            base_hue = (button_idx * 360 / self.button_count) % 360
            
            # Apply offset
            final_hue = (base_hue + hue_offset) % 360
            color = AnimationHelpers.hsv_to_pixel(final_hue, 0.93, 1.0)
            
            # Fill segment
            for i in range(segment_start, segment_end):
                self.strip[i] = color


class BoomsAnimation(Animation):
    """
    Booms animation - overlapping explosions with ripple effects.
    
    Multiple booms can be active simultaneously. Each boom expands with
    a ripple pattern (like water waves) and fades gradually, spreading
    far across the strip for minimal black areas.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 20):
        """
        Initialize booms animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds
        """
        super().__init__(strip, speed_ms)
        self.num_pixels: int = strip.num_pixels()
        
        # Track multiple active booms (list of boom dictionaries)
        self.active_booms: List[dict] = []
        self.frames_since_last_boom: int = 0
        self.boom_interval: int = 15  # Start new boom every 15 frames (overlapping)
        
        # Initialize strip to black
        from led_system.pixel import Pixel
        self.black = Pixel(0, 0, 0)
        for i in range(self.num_pixels):
            strip[i] = self.black
    
    def _create_boom(self) -> dict:
        """Create a new boom with random properties"""
        import random
        return {
            'center': random.randint(0, self.num_pixels - 1),
            'radius': 0.0,
            'max_radius': random.randint(40, 60),  # Larger radius for less black
            'hue': random.random() * 360,
            'age': 0,
            'speed': random.uniform(2.5, 3.5)  # Faster expansion
        }
    
    def _get_ripple_brightness(self, distance: float, radius: float, max_radius: float, age: int) -> float:
        """
        Calculate brightness with ripple effect.
        
        Creates a pattern like: x x x+1 x+1 x+2 x+2 x+1 x+1 x...
        """
        import math
        
        if distance > radius:
            return 0.0
        
        # Base brightness (bright at center, fades outward)
        base_brightness = 1.0 - (distance / max_radius) * 0.5
        
        # Ripple effect: creates waves using sine
        # Frequency increases with distance from center
        ripple_freq = 0.3  # How many ripples
        ripple = math.sin((distance - radius) * ripple_freq * math.pi) * 0.5 + 0.5
        
        # Combine base brightness with ripple
        final_brightness = base_brightness * (0.6 + ripple * 0.4)
        
        # Fade out over time (but slowly)
        age_factor = max(0, 1.0 - (age / 80.0))  # Slow fade over 80 frames
        
        return final_brightness * age_factor
    
    def advance(self) -> None:
        """Update all booms - expand, fade, and spawn new ones"""
        from game_system.animation_helpers import AnimationHelpers
        import random
        
        # Spawn new boom if interval passed
        self.frames_since_last_boom += 1
        if self.frames_since_last_boom >= self.boom_interval:
            self.active_booms.append(self._create_boom())
            self.frames_since_last_boom = 0
        
        # Clear strip (will redraw all booms)
        for i in range(self.num_pixels):
            self.strip[i] = self.black
        
        # Update and render all active booms
        booms_to_remove = []
        for boom_idx, boom in enumerate(self.active_booms):
            # Expand boom
            boom['radius'] += boom['speed']
            boom['age'] += 1
            
            # Render this boom with ripple effect
            for i in range(self.num_pixels):
                distance = abs(i - boom['center'])
                
                if distance <= boom['radius']:
                    brightness = self._get_ripple_brightness(
                        distance, 
                        boom['radius'], 
                        boom['max_radius'], 
                        boom['age']
                    )
                    
                    if brightness > 0.05:  # Only render if visible
                        # Get existing pixel color
                        existing_pixel = self.strip[i]
                        existing_h, existing_s, existing_v = AnimationHelpers._rgb_to_hsv(
                            existing_pixel.r, existing_pixel.g, existing_pixel.b
                        )
                        
                        # New color from this boom
                        new_color = AnimationHelpers.hsv_to_pixel(boom['hue'], 0.95, brightness)
                        
                        # Blend with existing (additive-like blending)
                        if existing_v > 0.05:
                            # Mix colors if pixel already lit
                            blended_h = (existing_h + boom['hue']) / 2
                            blended_v = min(1.0, existing_v + brightness * 0.5)
                            blended_color = AnimationHelpers.hsv_to_pixel(blended_h, 0.95, blended_v)
                            self.strip[i] = blended_color
                        else:
                            self.strip[i] = new_color
            
            # Remove boom if fully faded
            if boom['age'] > 80:  # Complete lifecycle
                booms_to_remove.append(boom_idx)
        
        # Remove completed booms (reverse order to maintain indices)
        for idx in reversed(booms_to_remove):
            self.active_booms.pop(idx)


class SparkleFlowAnimation(Animation):
    """
    Sparkle Flow animation - flowing streams of sparkles with color gradients.
    
    Creates multiple flowing "streams" of bright sparkles that travel along
    the strip, each with its own color gradient. Sparkles twinkle and shimmer
    as they move, creating a magical, flowing effect with depth.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 25):
        """
        Initialize sparkle flow animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds
        """
        super().__init__(strip, speed_ms)
        self.num_pixels: int = strip.num_pixels()
        
        # Track multiple sparkle streams
        self.streams: List[dict] = []
        self.max_streams: int = 5
        self.frames_since_last_stream: int = 0
        self.stream_interval: int = 20  # New stream every 20 frames
        
        # Initialize strip
        from led_system.pixel import Pixel
        self.black = Pixel(0, 0, 0)
        for i in range(self.num_pixels):
            strip[i] = self.black
    
    def _create_stream(self) -> dict:
        """Create a new sparkle stream with random properties"""
        import random
        return {
            'position': random.choice([0, self.num_pixels - 1]),  # Start from either end
            'direction': 1 if random.random() > 0.5 else -1,
            'hue': random.random() * 360,
            'hue_shift': random.uniform(-2, 2),  # Hue changes as stream moves
            'speed': random.uniform(1.5, 2.5),
            'sparkle_density': random.uniform(0.3, 0.6),  # How many pixels sparkle
            'age': 0,
            'lifetime': random.randint(80, 120)  # How long stream lasts
        }
    
    def _get_sparkle_brightness(self, position: float, stream_pos: float, 
                                  stream_age: int, stream_lifetime: int) -> float:
        """Calculate sparkle brightness with twinkling effect"""
        import random
        import math
        
        distance = abs(position - stream_pos)
        
        # Sparkles form a comet tail
        if distance > 20:
            return 0.0
        
        # Base brightness (bright at head, fades in tail)
        base_brightness = 1.0 - (distance / 20.0) * 0.7
        
        # Twinkle effect (random variations)
        twinkle = random.uniform(0.5, 1.0)
        
        # Pulse effect (breathing)
        pulse = (math.sin(stream_age * 0.2) + 1) / 2 * 0.3 + 0.7
        
        # Lifetime fade (fade in at start, fade out at end)
        if stream_age < 10:
            lifetime_factor = stream_age / 10.0
        elif stream_age > stream_lifetime - 15:
            lifetime_factor = (stream_lifetime - stream_age) / 15.0
        else:
            lifetime_factor = 1.0
        
        return base_brightness * twinkle * pulse * lifetime_factor
    
    def advance(self) -> None:
        """Update sparkle streams and render"""
        from game_system.animation_helpers import AnimationHelpers
        import random
        
        # Spawn new stream if needed
        self.frames_since_last_stream += 1
        if self.frames_since_last_stream >= self.stream_interval and len(self.streams) < self.max_streams:
            self.streams.append(self._create_stream())
            self.frames_since_last_stream = 0
        
        # Fade existing pixels (create trails)
        for i in range(self.num_pixels):
            pixel = self.strip[i]
            h, s, v = AnimationHelpers._rgb_to_hsv(pixel.r, pixel.g, pixel.b)
            if v > 0:
                new_v = max(0, v - 0.08)  # Gentle fade
                self.strip[i] = AnimationHelpers.hsv_to_pixel(h, s, new_v)
        
        # Update and render streams
        streams_to_remove = []
        for stream_idx, stream in enumerate(self.streams):
            # Move stream
            stream['position'] += stream['direction'] * stream['speed']
            stream['age'] += 1
            stream['hue'] = (stream['hue'] + stream['hue_shift']) % 360
            
            # Check if stream left the strip
            if stream['position'] < -20 or stream['position'] > self.num_pixels + 20:
                streams_to_remove.append(stream_idx)
                continue
            
            # Check if stream lifetime expired
            if stream['age'] > stream['lifetime']:
                streams_to_remove.append(stream_idx)
                continue
            
            # Render sparkles in this stream
            for offset in range(-20, 5):  # Comet tail
                pixel_idx = int(stream['position']) + offset
                
                if 0 <= pixel_idx < self.num_pixels:
                    # Random sparkle density
                    if random.random() < stream['sparkle_density']:
                        brightness = self._get_sparkle_brightness(
                            pixel_idx,
                            stream['position'],
                            stream['age'],
                            stream['lifetime']
                        )
                        
                        if brightness > 0.1:
                            # Calculate hue with gradient along tail
                            tail_progress = (offset + 20) / 25.0  # 0 at tail end, 1 at head
                            sparkle_hue = (stream['hue'] + tail_progress * 30) % 360
                            
                            # Get existing pixel
                            existing_pixel = self.strip[pixel_idx]
                            existing_h, existing_s, existing_v = AnimationHelpers._rgb_to_hsv(
                                existing_pixel.r, existing_pixel.g, existing_pixel.b
                            )
                            
                            # Additive blending
                            if existing_v > 0.1:
                                blended_v = min(1.0, existing_v + brightness * 0.5)
                                blended_h = (existing_h + sparkle_hue) / 2
                                self.strip[pixel_idx] = AnimationHelpers.hsv_to_pixel(blended_h, 0.9, blended_v)
                            else:
                                self.strip[pixel_idx] = AnimationHelpers.hsv_to_pixel(sparkle_hue, 0.9, brightness)
        
        # Remove completed streams
        for idx in reversed(streams_to_remove):
            self.streams.pop(idx)


class RainbowScrollAnimation(Animation):
    """
    Rainbow scroll animation - scrolls the rainbow pattern left and right.
    
    Continuously shifts the pixel pattern, creating a flowing movement effect.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 30):
        """
        Initialize rainbow scroll animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Scroll speed (milliseconds per pixel shift)
        """
        super().__init__(strip, speed_ms)
        self.num_pixels: int = strip.num_pixels()
        
        # Lazy initialization - capture pattern on first advance()
        self.base_pattern: Optional[List['Pixel']] = None
        
        # Scroll state
        self.scroll_offset: int = 0
        self.scroll_direction: int = 1  # 1 = right, -1 = left
        self.pixels_to_scroll: int = self.num_pixels // 4  # Scroll 1/4 strip before reversing
        self.pixels_scrolled: int = 0
    
    def advance(self) -> None:
        """Shift the pattern and render"""
        from led_system.pixel import Pixel
        
        # Capture pattern on first call (lazy initialization)
        if self.base_pattern is None:
            self.base_pattern = []
            for i in range(self.num_pixels):
                pixel = self.strip[i]
                self.base_pattern.append(Pixel(pixel.r, pixel.g, pixel.b))
        
        # Update scroll offset
        self.scroll_offset += self.scroll_direction
        self.pixels_scrolled += 1
        
        # Reverse direction after scrolling 1/4 of strip
        if self.pixels_scrolled >= self.pixels_to_scroll:
            self.scroll_direction *= -1
            self.pixels_scrolled = 0
        
        # Render scrolled pattern (with wrapping)
        for i in range(self.num_pixels):
            source_idx = (i - self.scroll_offset) % self.num_pixels
            self.strip[i] = self.base_pattern[source_idx]


class PartyAnimation(Animation):
    """
    Party animation with red override and dot projectile effects.
    
    Combines a sequence of underlying animations with:
    - Red override for reduction feature (buttons A and B)
    - Dot projectiles fired from button segments (other buttons)
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = None, button_count: int = None):
        """
        Initialize party animation with composite child animations.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds (unused, kept for compatibility)
            button_count: Number of buttons for reduction feature
        """
        super().__init__(strip, 20)  # Fixed 20ms for parent wrapper
        self.num_pixels: int = strip.num_pixels()
        
        # Reduction red override state
        self.button_count = button_count
        self.leds_per_button = strip.num_pixels() // button_count if button_count else 0
        self.button_A = None
        self.button_B = None
        self.a_red_pixels = 0  # Additional spread pixels (not including segment)
        self.b_red_pixels = 0  # Additional spread pixels (not including segment)
        self.button_A_held = False
        self.button_B_held = False
        
        # Dot projectile system
        self.active_dots: List[dict] = []  # List of active dot projectiles
        self.dot_speed: float = 3.0  # Pixels per frame
        self.dot_width: int = 3  # Width of each dot (pixels)
        
        # Pre-calculate button colors (each button gets unique hue)
        self.button_hues: List[float] = []
        if button_count:
            for i in range(button_count):
                hue = (i * 360 / button_count) % 360
                self.button_hues.append(hue)
        
        # Create child animation sequence
        # Phase 1: Win effect (rainbow fill from segment centers)
        win_effect = WinEffectAnimation(strip, button_count, speed_ms=50)
        win_duration = (self.leds_per_button / 2) * 0.05  # (ledsPerButton/2)*50ms
        
        # Phase 2: Rainbow blink (5 blinks, 200ms per state = 2 seconds total)
        rainbow_blink = RainbowBlinkAnimation(strip, blink_count=5, speed_ms=200)
        blink_duration = 5 * 2 * 0.2  # 5 blinks × 2 states × 200ms
        
        # Phase 3: Rainbow scroll (5 seconds)
        rainbow_scroll = RainbowScrollAnimation(strip, speed_ms=30)
        
        # Phase 4: Random repeating sequence of party animations
        # Create animations for the random sequence
        pushing_bands = PushingBandsAnimation(strip, speed_ms=None)
        rainbow_sin = RainbowSinWaveAnimation(strip, speed_ms=50)
        booms = BoomsAnimation(strip, speed_ms=20)  # Faster speed
        sparkle_flow = SparkleFlowAnimation(strip, speed_ms=25)  # New creative animation
        
        # Randomize order
        party_animations = [
            (pushing_bands, 20.0),  # 20 seconds each
            (rainbow_sin, 20.0),
            (booms, 20.0),
            (sparkle_flow, 20.0)
        ]
        random.shuffle(party_animations)
        
        # Create repeating random sequence
        random_party_loop = SequenceAnimation(
            strip=strip,
            animation_sequence=party_animations,
            repeat=True,  # Loop forever
            frame_speed_ms=20
        )
        
        self.child_animation = SequenceAnimation(
            strip=strip,
            animation_sequence=[
                (win_effect, win_duration),
                (rainbow_blink, blink_duration),
                (rainbow_scroll, 5.0),  # 5 seconds
                (random_party_loop, None)  # Continuous loop
            ],
            repeat=False,
            frame_speed_ms=20
        )
    
    def trigger_dot(self, button_index: int) -> None:
        """
        Trigger a dot projectile from a button segment.
        
        Args:
            button_index: Index of button that fired the dot
        """
        if button_index >= self.button_count:
            return
        
        # Calculate segment center position
        segment_start = button_index * self.leds_per_button
        segment_end = (button_index + 1) * self.leds_per_button
        center_pos = (segment_start + segment_end) / 2.0
        
        # Create new dot projectile
        dot = {
            'origin': center_pos,
            'left_pos': center_pos,
            'right_pos': center_pos,
            'hue': self.button_hues[button_index] if button_index < len(self.button_hues) else 0,
            'active': True
        }
        self.active_dots.append(dot)
    
    def _update_dots(self) -> None:
        """Update all active dot projectiles"""
        dots_to_remove = []
        
        for dot_idx, dot in enumerate(self.active_dots):
            # Move dots outward in both directions
            dot['left_pos'] -= self.dot_speed
            dot['right_pos'] += self.dot_speed
            
            # Check if both dots are off-screen
            if dot['left_pos'] < -self.dot_width and dot['right_pos'] > self.num_pixels + self.dot_width:
                dots_to_remove.append(dot_idx)
        
        # Remove completed dots (reverse order to maintain indices)
        for idx in reversed(dots_to_remove):
            self.active_dots.pop(idx)
    
    def _render_dots(self) -> None:
        """Render all active dot projectiles on top of base animation"""
        from game_system.animation_helpers import AnimationHelpers
        
        for dot in self.active_dots:
            color = AnimationHelpers.hsv_to_pixel(dot['hue'], 1.0, 1.0)
            
            # Render left-traveling dot
            left_center = int(dot['left_pos'])
            for offset in range(-self.dot_width, self.dot_width + 1):
                pixel_idx = left_center + offset
                if 0 <= pixel_idx < self.num_pixels:
                    # Brightness falloff from center
                    brightness_factor = 1.0 - (abs(offset) / (self.dot_width + 1))
                    dot_color = AnimationHelpers.hsv_to_pixel(
                        dot['hue'], 
                        1.0, 
                        brightness_factor
                    )
                    self.strip[pixel_idx] = dot_color
            
            # Render right-traveling dot
            right_center = int(dot['right_pos'])
            for offset in range(-self.dot_width, self.dot_width + 1):
                pixel_idx = right_center + offset
                if 0 <= pixel_idx < self.num_pixels:
                    # Brightness falloff from center
                    brightness_factor = 1.0 - (abs(offset) / (self.dot_width + 1))
                    dot_color = AnimationHelpers.hsv_to_pixel(
                        dot['hue'], 
                        1.0, 
                        brightness_factor
                    )
                    self.strip[pixel_idx] = dot_color
    
    def advance(self) -> None:
        """Render child animation, then apply overrides on top"""
        # Let child animation render first
        self.child_animation.update_if_needed()
        
        # Update and render dot projectiles
        self._update_dots()
        self._render_dots()
        
        # Apply red override on top if any buttons held (highest priority)
        if self.button_A_held or self.button_B_held:
            self._apply_red_override()
    
    def set_red_override(self, button_A: int, button_B: int, 
                         a_red_pixels: int, b_red_pixels: int,
                         button_A_held: bool, button_B_held: bool) -> None:
        """
        Set red override information for reduction feature.
        
        Args:
            button_A: Index of button A (right center)
            button_B: Index of button B (left center)
            a_red_pixels: Number of additional spread pixels from A (not including segment)
            b_red_pixels: Number of additional spread pixels from B (not including segment)
            button_A_held: Whether button A is currently held
            button_B_held: Whether button B is currently held
        """
        self.button_A = button_A
        self.button_B = button_B
        self.a_red_pixels = a_red_pixels
        self.b_red_pixels = b_red_pixels
        self.button_A_held = button_A_held
        self.button_B_held = button_B_held
    
    def _apply_red_override(self) -> None:
        """Apply red color override for reduction feature"""
        if not self.button_A_held and not self.button_B_held:
            return  # No buttons held, no override needed
        
        from led_system.pixel import Pixel
        red = Pixel(255, 0, 0)
        
        # Button A held: segment + spread right
        if self.button_A_held:
            # Segment always red when held
            segment_start = self.button_A * self.leds_per_button
            segment_end = (self.button_A + 1) * self.leds_per_button
            self.strip[segment_start:segment_end] = red
            
            # Additional spread pixels beyond segment
            if self.a_red_pixels > 0:
                spread_start = segment_end
                spread_end = spread_start + self.a_red_pixels
                self.strip[spread_start:spread_end] = red
        
        # Button B held: segment + spread left
        if self.button_B_held:
            # Segment always red when held
            segment_start = self.button_B * self.leds_per_button
            segment_end = (self.button_B + 1) * self.leds_per_button
            self.strip[segment_start:segment_end] = red
            
            # Additional spread pixels before segment
            if self.b_red_pixels > 0:
                spread_end = segment_start
                spread_start = max(0, spread_end - self.b_red_pixels)
                self.strip[spread_start:spread_end] = red


class CodeModeAnimation(Animation):
    """
    Animation for code input mode - fills strip with blue gradient on enter,
    then shows green segments for active digits (green overrides blue).
    
    Green segments fade from bright to darker as more digits are entered.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, speed_ms: int = 20):
        """
        Initialize code mode animation.
        
        Args:
            strip: LED strip to operate on
            button_count: Number of buttons (for segment calculation)
            speed_ms: Animation update interval
        """
        super().__init__(strip, speed_ms)
        self.button_count: int = button_count
        self.leds_per_button: int = strip.num_pixels() // button_count
        self.num_pixels = strip.num_pixels()
        self.active_digits_ordered: List[int] = []  # Ordered list of digits in sequence
        
        # Pre-calculate blue gradient for entire strip (darker → lighter)
        from game_system.animation_helpers import AnimationHelpers
        self.blue_gradient_colors = []
        for i in range(self.num_pixels):
            progress = i / max(1, self.num_pixels - 1)
            hue = 240 - (progress * 40)  # 240 (pure blue) → 200 (cyan-blue)
            value = 0.4 + (progress * 0.6)  # 0.4 → 1.0 (darker → lighter)
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, value)
            self.blue_gradient_colors.append(color)
        
        # Fill animation state (permutation-based fill)
        self.fill_complete = False
        self.pixel_index = 0
        self.strip_index = 0  # Strip 0 for button strip
        
        # Start with all black
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for i in range(self.num_pixels):
            strip[i] = black
    
    def set_active_digits(self, sequence: str) -> None:
        """
        Update which button digits should be lit based on sequence.
        
        Args:
            sequence: Current sequence string (e.g., "314")
        """
        # Store ordered list of digits to track sequence order
        self.active_digits_ordered = []
        for char in sequence:
            if char.isdigit():
                self.active_digits_ordered.append(int(char))
    
    def advance(self) -> None:
        """
        Update strip:
        1. Fill blue gradient via permutation (if not complete)
        2. Always render blue gradient as base
        3. Override with green segments for active digits (fading brightness)
        """
        from game_system.animation_helpers import STRIP_PERMUTATIONS, AnimationHelpers
        from led_system.pixel import Pixel
        
        # Phase 1: Fill blue gradient by permutation
        if not self.fill_complete:
            if self.strip_index in STRIP_PERMUTATIONS:
                permutation = STRIP_PERMUTATIONS[self.strip_index]
                
                # Fill 8 pixels per advance (very fast)
                pixels_per_advance = 8
                for _ in range(pixels_per_advance):
                    if self.pixel_index < len(permutation):
                        pixel_to_fill = permutation[self.pixel_index]
                        self.strip[pixel_to_fill] = self.blue_gradient_colors[pixel_to_fill]
                        self.pixel_index += 1
                    else:
                        self.fill_complete = True
                        break
        
        # Phase 2: Always render base blue gradient (if fill complete)
        if self.fill_complete:
            for i in range(self.num_pixels):
                self.strip[i] = self.blue_gradient_colors[i]
        
        # Phase 3: Override with green segments (color shifts from green-yellow to green-blue)
        if self.active_digits_ordered:
            for seq_index, button_index in enumerate(self.active_digits_ordered):
                if button_index < self.button_count:
                    # Calculate hue shift: green-yellow → pure green → green-blue
                    # Hue 90 = green-yellow, 120 = pure green, 150 = green-blue
                    # First digit: 90 (green-yellow)
                    # Last digit (5th): 150 (green-blue)
                    hue = 90 + (seq_index * 15)  # Shift 15 degrees per digit
                    
                    # All segments at full brightness and saturation
                    green = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
                    
                    # Fill this segment
                    start_idx = button_index * self.leds_per_button
                    end_idx = (button_index + 1) * self.leds_per_button
                    for i in range(start_idx, end_idx):
                        self.strip[i] = green


class CodeRevealFillAnimation(Animation):
    """
    Progressive fill animation for code reveal.
    
    Lights up one more digit each advance until all are revealed.
    Uses same green color progression as CodeModeAnimation.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, code_sequence: str, speed_ms: int = 200):
        super().__init__(strip, speed_ms)
        
        self.button_count: int = button_count
        self.leds_per_button: int = strip.num_pixels() // button_count
        
        # Parse code sequence
        self.code_digits: List[int] = [int(char) for char in code_sequence if char.isdigit()]
        
        # Pre-calculate green colors for each digit
        self.digit_colors = []
        for seq_index in range(len(self.code_digits)):
            hue = 90 + (seq_index * 15)  # 90, 105, 120, 135, 150
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
            self.digit_colors.append(color)
        
        # Animation state
        self.revealed_count: int = 0  # How many digits are currently revealed
        
        # Start with all black
        self.strip[:] = AnimationHelpers.BLACK
    
    def advance(self) -> None:
        """Reveal one more digit, then keep rendering all revealed digits"""
        # Increment revealed count (but not beyond total)
        if self.revealed_count < len(self.code_digits):
            self.revealed_count += 1
        
        # Render all currently revealed digits
        for seq_index in range(self.revealed_count):
            digit = self.code_digits[seq_index]
            digit_color = self.digit_colors[seq_index]
            
            start_idx = digit * self.leds_per_button
            end_idx = (digit + 1) * self.leds_per_button
            self.strip[start_idx:end_idx] = digit_color


class CodeRevealBlinkAnimation(Animation):
    """
    Blink animation for code reveal.
    
    Blinks all code digit segments with their respective hue-shifted colors.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, code_sequence: str, speed_ms: int = 400):
        super().__init__(strip, speed_ms)
        
        self.button_count: int = button_count
        self.leds_per_button: int = strip.num_pixels() // button_count
        
        # Parse code sequence
        self.code_digits: List[int] = [int(char) for char in code_sequence if char.isdigit()]
        
        # Pre-calculate green colors for each digit
        self.digit_colors = []
        for seq_index in range(len(self.code_digits)):
            hue = 90 + (seq_index * 15)
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
            self.digit_colors.append(color)
        
        # Start with digits shown (will toggle to black on first advance)
        self.blink_state: bool = False  # Will toggle to True on first advance
        
        # Render initial state (all digits lit)
        for seq_index, digit in enumerate(self.code_digits):
            start_idx = digit * self.leds_per_button
            end_idx = (digit + 1) * self.leds_per_button
            self.strip[start_idx:end_idx] = self.digit_colors[seq_index]
    
    def advance(self) -> None:
        """Toggle blink state and render all digits"""
        self.blink_state = not self.blink_state
        
        # Render all code digit segments
        for seq_index, digit in enumerate(self.code_digits):
            start_idx = digit * self.leds_per_button
            end_idx = (digit + 1) * self.leds_per_button
            
            # Use hue-shifted color if on, black if off
            color = self.digit_colors[seq_index] if self.blink_state else AnimationHelpers.BLACK
            self.strip[start_idx:end_idx] = color


def create_code_reveal_button_animation(strip: 'LedStrip', button_count: int, code_sequence: str) -> SequenceAnimation:
    """
    Factory function to create button strip code reveal animation.
    
    Phases:
    1. Progressive fill - reveal one digit at a time (200ms per digit)
    2. Continuous blink - blink all revealed digits (400ms cycle)
    
    Args:
        strip: LED strip to animate
        button_count: Number of buttons for segment calculation
        code_sequence: Code sequence to reveal (e.g., "314")
        
    Returns:
        SequenceAnimation with fill and blink phases
    """
    fill_anim = CodeRevealFillAnimation(strip, button_count, code_sequence, speed_ms=200)
    blink_anim = CodeRevealBlinkAnimation(strip, button_count, code_sequence, speed_ms=400)
    
    # Calculate fill duration based on number of digits
    num_digits = len([c for c in code_sequence if c.isdigit()])
    # Add one extra interval so last digit is visible for 200ms before transition
    fill_duration = (num_digits + 1) * 0.2  # 200ms per digit + 200ms for last digit
    
    return SequenceAnimation(
        strip=strip,
        animation_sequence=[
            (fill_anim, fill_duration),  # Fill all digits
            (blink_anim, None)           # Continuous blink
        ],
        repeat=False,
        frame_speed_ms=20
    )


class BlueGradientBlinkPyramidAnimation(Animation):
    """Blue gradient blink animation for pyramid - blinks blue gradient on/off."""
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 100):
        super().__init__(strip, speed_ms)
        
        # Pre-calculate blue gradient colors (same as CodeModePyramidAnimation)
        from game_system.animation_helpers import AnimationHelpers
        self.blue_gradient_colors = []
        for i in range(strip.num_pixels()):
            progress = i / max(1, strip.num_pixels() - 1)
            hue = 240 - (progress * 40)  # 240 (pure blue) → 200 (cyan-blue)
            value = 0.4 + (progress * 0.6)  # 0.4 → 1.0 (darker → lighter)
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, value)
            self.blue_gradient_colors.append(color)
        
        self.blink_state = True  # True = on, False = off
    
    def advance(self) -> None:
        """Toggle between blue gradient and black"""
        from led_system.pixel import Pixel
        
        self.blink_state = not self.blink_state
        
        if self.blink_state:
            # On - show blue gradient
            for i in range(self.strip.num_pixels()):
                self.strip[i] = self.blue_gradient_colors[i]
        else:
            # Off - black
            black = Pixel(0, 0, 0)
            for i in range(self.strip.num_pixels()):
                self.strip[i] = black


class PyramidHeightFillAnimation(Animation):
    """
    Progressive fill animation for pyramid - fills height segments one by one.
    
    Reveals height segments [0:20], [20:40], [40:60], [60:80], [80:100] progressively,
    each colored with the corresponding code sequence digit color.
    Synchronized with button strip code reveal (200ms per segment).
    """
    
    def __init__(self, strip: 'LedStrip', code_sequence: str, speed_ms: int = 200):
        super().__init__(strip, speed_ms)
        
        from game_system.animation_helpers import AnimationHelpers, pyramidHeight
        
        # Parse code sequence
        code_digits = [int(char) for char in code_sequence if char.isdigit()]
        
        # Pre-calculate green colors for each sequence digit
        self.digit_colors = []
        for seq_index in range(len(code_digits)):
            hue = 90 + (seq_index * 15)  # Same as CodeModeAnimation
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
            self.digit_colors.append(color)
        
        # Pre-calculate height zones and their pixel sets
        self.height_zones = []
        for zone_index in range(5):
            start_height = zone_index * 20
            end_height = start_height + 20
            zone_pixels = pyramidHeight[start_height:end_height]
            
            # Get color for this zone (or fallback to last color)
            if zone_index < len(self.digit_colors):
                zone_color = self.digit_colors[zone_index]
            else:
                zone_color = self.digit_colors[-1] if self.digit_colors else AnimationHelpers.hsv_to_pixel(120, 1.0, 1.0)
            
            self.height_zones.append((zone_pixels, zone_color))
        
        # Animation state
        self.revealed_count: int = 0  # How many zones are currently revealed
        
        # Start with all black
        self.strip[:] = AnimationHelpers.BLACK
    
    def advance(self) -> None:
        """Reveal one more height zone, then keep rendering all revealed zones"""
        # Increment revealed count (but not beyond total zones)
        if self.revealed_count < len(self.height_zones):
            self.revealed_count += 1
        
        # Render all currently revealed zones
        for zone_index in range(self.revealed_count):
            zone_pixels, zone_color = self.height_zones[zone_index]
            for pixel_idx in zone_pixels:
                self.strip[pixel_idx] = zone_color


class GreenGradientBlinkPyramidAnimation(Animation):
    """
    Green gradient blink animation for pyramid - uses code sequence colors by height.
    
    Divides pyramid into 5 height zones (0-20, 20-40, 40-60, 60-80, 80-100),
    each colored with the corresponding code sequence digit color.
    """
    
    def __init__(self, strip: 'LedStrip', code_sequence: str, speed_ms: int = 100):
        super().__init__(strip, speed_ms)
        
        from game_system.animation_helpers import AnimationHelpers
        
        # Pre-calculate green colors for each sequence digit
        code_digits = [int(char) for char in code_sequence if char.isdigit()]
        self.digit_colors = []
        for seq_index in range(len(code_digits)):
            hue = 90 + (seq_index * 15)  # Same as CodeModeAnimation
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
            self.digit_colors.append(color)
        
        # Pre-calculate which color each pixel should be based on height
        from game_system.animation_helpers import pyramidHeight
        self.pixel_colors = []
        
        for i in range(strip.num_pixels()):
            # Determine which height zone this pixel belongs to
            pixel_color = None
            for height_zone in range(5):
                start_height = height_zone * 20
                end_height = start_height + 20
                zone_pixels = pyramidHeight[start_height:end_height]
                
                if i in zone_pixels:
                    # Use corresponding digit color (if available)
                    if height_zone < len(self.digit_colors):
                        pixel_color = self.digit_colors[height_zone]
                    else:
                        # Fallback to last color if sequence is shorter than 5
                        pixel_color = self.digit_colors[-1] if self.digit_colors else AnimationHelpers.hsv_to_pixel(120, 1.0, 1.0)
                    break
            
            # Store color for this pixel
            self.pixel_colors.append(pixel_color if pixel_color else AnimationHelpers.hsv_to_pixel(120, 1.0, 1.0))
        
        self.blink_state = True  # True = on, False = off
    
    def advance(self) -> None:
        """Toggle between green gradient and black"""
        from led_system.pixel import Pixel
        
        self.blink_state = not self.blink_state
        
        if self.blink_state:
            # On - show green gradient by height
            for i in range(self.strip.num_pixels()):
                self.strip[i] = self.pixel_colors[i]
        else:
            # Off - black
            black = Pixel(0, 0, 0)
            for i in range(self.strip.num_pixels()):
                self.strip[i] = black


class PyramidVerticalFillByPieces(Animation):
    """
    Fills pyramid vertically in pieces - even pieces (0,2,4,...,18) then odd pieces (1,3,5,...,19).
    Each piece is 5% of pyramid height.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 80):
        super().__init__(strip, speed_ms)
        
        self.fill_pieces_lit = 0  # How many pieces have been lit (0-20)
        self.fill_stage = 'even'  # 'even' → 'odd'
        
        # Start with all black
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for i in range(strip.num_pixels()):
            strip[i] = black
    
    def advance(self) -> None:
        """Light next piece in sequence"""
        from game_system.animation_helpers import pyramidHeight
        from led_system.pixel import Pixel
        
        white = Pixel(255, 255, 255)
        
        if self.fill_stage == 'even':
            # Light even pieces: 0, 2, 4, ..., 18
            piece_index = self.fill_pieces_lit * 2
            
            if piece_index < 20:
                # Calculate height range for this piece (each piece is 5% of pyramid)
                start_height = piece_index * 5
                end_height = start_height + 5
                
                # Light this piece
                piece_pixels = pyramidHeight[start_height:end_height]
                for pixel_idx in piece_pixels:
                    self.strip[pixel_idx] = white
                
                self.fill_pieces_lit += 1
            else:
                # All even pieces lit, switch to odd
                self.fill_stage = 'odd'
                self.fill_pieces_lit = 0
        
        else:  # fill_stage == 'odd'
            # Light odd pieces: 1, 3, 5, ..., 19
            piece_index = self.fill_pieces_lit * 2 + 1
            
            if piece_index < 20:
                # Calculate height range for this piece
                start_height = piece_index * 5
                end_height = start_height + 5
                
                # Light this piece
                piece_pixels = pyramidHeight[start_height:end_height]
                for pixel_idx in piece_pixels:
                    self.strip[pixel_idx] = white
                
                self.fill_pieces_lit += 1


class WhiteBlinkPyramidAnimation(Animation):
    """Blinks entire pyramid white/black."""
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 400):
        super().__init__(strip, speed_ms)
        self.blink_state = True  # True = on, False = off
    
    def advance(self) -> None:
        """Toggle between white and black"""
        from led_system.pixel import Pixel
        
        self.blink_state = not self.blink_state
        
        if self.blink_state:
            # On - white
            white = Pixel(255, 255, 255)
            for i in range(self.strip.num_pixels()):
                self.strip[i] = white
        else:
            # Off - black
            black = Pixel(0, 0, 0)
            for i in range(self.strip.num_pixels()):
                self.strip[i] = black


def create_code_reveal_pyramid_animation(strip: 'LedStrip', code_sequence: str = "") -> SequenceAnimation:
    """
    Factory function to create code reveal pyramid animation sequence.
    
    Phases:
    1. Progressive height fill - reveal segments [0:20], [20:40], [40:60], [60:80], [80:100]
       one by one with code sequence colors (200ms per segment, synchronized with button reveals)
    2. Clear to black (brief transition)
    3. White vertical fill by pieces - even then odd (1.6 seconds)
    4. White blink (continuous)
    
    Args:
        strip: LED strip to animate (pyramid strip)
        code_sequence: The code sequence for color mapping (e.g., "314")
        
    Returns:
        SequenceAnimation with all phases
    """
    from led_system.pixel import Pixel
    
    # Calculate fill duration based on number of digits/zones
    num_digits = len([c for c in code_sequence if c.isdigit()]) if code_sequence else 5
    # Add one extra interval so last segment is visible for 200ms before transition
    fill_duration = (num_digits + 1) * 0.2  # 200ms per segment + 200ms for last segment
    
    # Phase 1: Progressive height fill with green colors
    if code_sequence:
        height_fill = PyramidHeightFillAnimation(strip, code_sequence, speed_ms=200)
    else:
        # Fallback to blue if no sequence
        height_fill = BlueGradientBlinkPyramidAnimation(strip, speed_ms=200)
        fill_duration = 1.0
    
    # Phase 2: Clear to black (brief transition)
    black = Pixel(0, 0, 0)
    clear_anim = SolidColorAnimation(strip, black, speed_ms=50)
    
    # Phase 3: White fill by pieces
    white_fill = PyramidVerticalFillByPieces(strip, speed_ms=80)
    
    # Phase 4: White blink
    white_blink = WhiteBlinkPyramidAnimation(strip, speed_ms=400)
    
    return SequenceAnimation(
        strip=strip,
        animation_sequence=[
            (height_fill, fill_duration),  # Progressive fill (num_digits × 200ms)
            (clear_anim, 0.05),            # 50ms clear to black
            (white_fill, 1.68),            # 1.68 seconds: 20 pieces × 80ms + 80ms for last piece to be visible
            (white_blink, None)            # Continuous white blink
        ],
        repeat=False,
        frame_speed_ms=20
    )


class SolidColorAnimation(Animation):
    """Displays a solid color across entire strip."""
    
    def __init__(self, strip: 'LedStrip', color: 'Pixel', speed_ms: int = 50):
        super().__init__(strip, speed_ms)
        self.color = color
    
    def advance(self) -> None:
        """Fill strip with solid color"""
        for i in range(self.strip.num_pixels()):
            self.strip[i] = self.color


class SegmentColorAnimation(Animation):
    """Displays a color on specific button segments, black elsewhere."""
    
    def __init__(self, strip: 'LedStrip', color: 'Pixel', segment_buttons: List[int], 
                 button_count: int, speed_ms: int = 50):
        super().__init__(strip, speed_ms)
        self.color = color
        self.segment_buttons = segment_buttons
        self.button_count = button_count
        self.leds_per_button = strip.num_pixels() // button_count
        
        from led_system.pixel import Pixel
        self.black = Pixel(0, 0, 0)
    
    def advance(self) -> None:
        """Fill specified segments with color, rest with black"""
        for i in range(self.strip.num_pixels()):
            button_index = i // self.leds_per_button
            
            if button_index in self.segment_buttons:
                self.strip[i] = self.color
            else:
                self.strip[i] = self.black


class ButtonReleasedAnimation(Animation):
    """
    Animation for button-released failure.
    
    Keeps sequence buttons green (with hue shift) and blinks the released button
    with the red failure pattern: red → black → darker red → black → darkest red.
    """
    
    def __init__(self, strip: 'LedStrip', sequence_buttons: List[int], released_button: int,
                 button_count: int, speed_ms: int = 50):
        super().__init__(strip, speed_ms)
        self.sequence_buttons = sequence_buttons
        self.released_button = released_button
        self.button_count = button_count
        self.leds_per_button = strip.num_pixels() // button_count
        
        from led_system.pixel import Pixel
        from game_system.animation_helpers import AnimationHelpers
        
        # Pre-calculate green colors for sequence buttons (with hue shift)
        self.green_colors = []
        for seq_index in range(len(sequence_buttons)):
            hue = 90 + (seq_index * 15)  # Same as CodeModeAnimation
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
            self.green_colors.append(color)
        
        # Red colors for blinking pattern
        self.red_bright = Pixel(255, 0, 0)
        self.red_medium = Pixel(150, 0, 0)
        self.red_dark = Pixel(80, 0, 0)
        self.black = Pixel(0, 0, 0)
        
        # Animation state for blinking
        self.phase_start_time = time.time()
        self.current_phase = 0  # 0-4 for the 5 phases
        self.phase_durations = [0.25, 0.25, 0.25, 0.25, 1.3]  # Same as failure animation
    
    def advance(self) -> None:
        """Update animation - green segments + blinking released button"""
        from game_system.animation_helpers import AnimationHelpers
        
        current_time = time.time()
        elapsed = current_time - self.phase_start_time
        
        # Check if should advance to next phase
        if self.current_phase < len(self.phase_durations):
            if elapsed >= self.phase_durations[self.current_phase]:
                self.current_phase += 1
                self.phase_start_time = current_time
        
        # Determine released button color based on phase
        if self.current_phase < len(self.phase_durations):
            phase_colors = [
                self.red_bright,   # Phase 0: bright red
                self.black,         # Phase 1: black
                self.red_medium,    # Phase 2: medium red
                self.black,         # Phase 3: black
                self.red_dark       # Phase 4: dark red constant
            ]
            released_color = phase_colors[self.current_phase]
        else:
            released_color = self.red_dark  # Stay dark red after phases complete
        
        # Render all pixels
        for i in range(self.strip.num_pixels()):
            button_index = i // self.leds_per_button
            
            if button_index == self.released_button:
                # Released button: blink with red pattern
                self.strip[i] = released_color
            elif button_index in self.sequence_buttons:
                # Sequence buttons: stay green with hue shift
                seq_position = self.sequence_buttons.index(button_index)
                self.strip[i] = self.green_colors[seq_position]
            else:
                # Other buttons: black
                self.strip[i] = self.black


class ColorBlinkAnimation(Animation):
    """Blinks between a color and black."""
    
    def __init__(self, strip: 'LedStrip', color: 'Pixel', speed_ms: int = 100):
        super().__init__(strip, speed_ms)
        self.color = color
        from led_system.pixel import Pixel
        self.black = Pixel(0, 0, 0)
        self.blink_state = False  # Start False so first toggle shows color (True)
    
    def advance(self) -> None:
        """Toggle between color and black"""
        self.blink_state = not self.blink_state
        
        display_color = self.color if self.blink_state else self.black
        for i in range(self.strip.num_pixels()):
            self.strip[i] = display_color


def create_button_released_failure_animation(strip: 'LedStrip', sequence_buttons: List[int], 
                                             released_button: int, button_count: int) -> 'Animation':
    """
    Factory function to create button-released failure animation.
    
    Shows green on sequence buttons and red blinking pattern on the released button.
    
    Args:
        strip: LED strip to animate
        sequence_buttons: List of button indices in the sequence
        released_button: Button index that was released
        button_count: Total number of buttons
        
    Returns:
        ButtonReleasedAnimation instance
    """
    return ButtonReleasedAnimation(strip, sequence_buttons, released_button, button_count, speed_ms=50)


def create_failure_animation(strip: 'LedStrip', sequence_buttons: List[int] = None, button_count: int = None) -> SequenceAnimation:
    """
    Factory function to create failure animation sequence.
    
    Progression: red → black → darker red → black → darkest red → stay 1.3s
    
    For button strip: Only lights red on sequence button segments (if provided)
    For pyramid strip: Lights entire strip red
    
    Phases:
    1. Red flash (250ms)
    2. Black (250ms)
    3. Darker red flash (250ms)
    4. Black (250ms)
    5. Darkest red constant (1300ms)
    
    Total duration: 2.3 seconds
    
    Args:
        strip: LED strip to animate
        sequence_buttons: List of button indices in the sequence (for button strip only)
        button_count: Total number of buttons (for segment calculation, button strip only)
        
    Returns:
        SequenceAnimation with all phases
    """
    from led_system.pixel import Pixel
    
    # Define red colors with decreasing brightness
    red_bright = Pixel(255, 0, 0)      # Bright red
    red_medium = Pixel(150, 0, 0)      # Medium/darker red
    red_dark = Pixel(80, 0, 0)         # Darkest red
    black = Pixel(0, 0, 0)             # Black
    
    # Create animations based on whether sequence buttons are provided
    if sequence_buttons is not None and button_count is not None:
        # Button strip: only light sequence segments
        flash1 = SegmentColorAnimation(strip, red_bright, sequence_buttons, button_count, speed_ms=50)
        black1 = SolidColorAnimation(strip, black, speed_ms=50)
        flash2 = SegmentColorAnimation(strip, red_medium, sequence_buttons, button_count, speed_ms=50)
        black2 = SolidColorAnimation(strip, black, speed_ms=50)
        constant_red = SegmentColorAnimation(strip, red_dark, sequence_buttons, button_count, speed_ms=50)
    else:
        # Pyramid strip: light entire strip
        flash1 = SolidColorAnimation(strip, red_bright, speed_ms=50)
        black1 = SolidColorAnimation(strip, black, speed_ms=50)
        flash2 = SolidColorAnimation(strip, red_medium, speed_ms=50)
        black2 = SolidColorAnimation(strip, black, speed_ms=50)
        constant_red = SolidColorAnimation(strip, red_dark, speed_ms=50)
    
    return SequenceAnimation(
        strip=strip,
        animation_sequence=[
            (flash1, 0.25),          # 250ms: bright red
            (black1, 0.25),          # 250ms: black
            (flash2, 0.25),          # 250ms: darker red
            (black2, 0.25),          # 250ms: black
            (constant_red, 1.3)      # 1300ms: darkest red constant
        ],
        repeat=False,
        frame_speed_ms=20
    )
