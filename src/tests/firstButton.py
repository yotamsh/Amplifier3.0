#!/usr/bin/env python3
"""
First Button Script - Dual LED Strip Control with Button Toggle
- 2 LED strips on GPIO18 and GPIO21 (300 LEDs each, 10% brightness)
- Button on GPIO2 to toggle between strips
- Infinite color wipe animation that switches strips on button press
- Press Ctrl+C to exit
"""
import time
import threading
from rpi_ws281x import PixelStrip, Color
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("⚠️  RPi.GPIO not available - this script is for Raspberry Pi only")
    import sys
    sys.exit(1)

# LED Strip Configuration
LED_COUNT = 300          # Number of LEDs per strip
LED_FREQ_HZ = 800000     # Signal frequency (800kHz)
LED_BRIGHTNESS = 26      # 10% brightness (0-255)
LED_INVERT = False       # Signal inversion

# Strip GPIOs and PWM channels
STRIP1_GPIO = 18         # GPIO18 (PWM0)
STRIP1_PWM = 0           # PWM channel 0
STRIP1_DMA = 10          # DMA channel 10

STRIP2_GPIO = 21         # GPIO21 
STRIP2_PWM = 0           # PWM channel 0 (different DMA)
STRIP2_DMA = 5           # DMA channel 5

# Button Configuration
BUTTON_GPIO = 25         # GPIO25 (external pull-down, HIGH when pressed)
DEBOUNCE_TIME = 0.2      # Button debounce time in seconds

# Animation Configuration
WIPE_DELAY = 0.01        # Delay between pixels (10ms = fast wipe)
COLOR_HOLD_TIME = 1.0    # Hold each color for 1 second

# Color palette for wipe animation
COLORS = [
    Color(255, 0, 0),    # Red
    Color(0, 255, 0),    # Green  
    Color(0, 0, 255),    # Blue
    Color(255, 255, 0),  # Yellow
    Color(255, 0, 255),  # Magenta
    Color(0, 255, 255),  # Cyan
    Color(255, 128, 0),  # Orange
    Color(128, 0, 255),  # Purple
]

class DualStripController:
    """Controller for dual LED strips with button toggle"""
    
    def __init__(self):
        self.current_strip = 0  # 0 = strip1, 1 = strip2
        self.running = True
        self.button_pressed = False
        self.last_button_time = 0
        
        # Setup button FIRST, before LED strips
        print(f"🔲 Setting up button on GPIO{BUTTON_GPIO}...")
        self.setup_button()
        
        # Initialize LED strips
        print("🔲 Initializing LED strips...")
        self.strip1 = PixelStrip(LED_COUNT, STRIP1_GPIO, LED_FREQ_HZ, 
                                STRIP1_DMA, LED_INVERT, LED_BRIGHTNESS, STRIP1_PWM)
        self.strip2 = PixelStrip(LED_COUNT, STRIP2_GPIO, LED_FREQ_HZ, 
                                STRIP2_DMA, LED_INVERT, LED_BRIGHTNESS, STRIP2_PWM)
        
        # Initialize strips
        self.strip1.begin()
        self.strip2.begin()
        
        # Clear both strips
        self.clear_strip(self.strip1)
        self.clear_strip(self.strip2)
        
        print("✅ Dual LED strips initialized:")
        print(f"   Strip 1: GPIO{STRIP1_GPIO} - {LED_COUNT} LEDs")
        print(f"   Strip 2: GPIO{STRIP2_GPIO} - {LED_COUNT} LEDs")
        print(f"   Brightness: {int(LED_BRIGHTNESS/255*100)}%")
        
    def setup_button(self):
        """Setup button GPIO without internal pull resistors (polling mode)"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
            print(f"✅ Button configured on GPIO{BUTTON_GPIO} (polling mode)")
            
        except Exception as e:
            print(f"❌ Button setup failed on GPIO{BUTTON_GPIO}: {e}")
            print(f"💡 Detailed error: {type(e).__name__}")
            raise
        
    def check_button(self):
        """Check button state (polling mode with debouncing)"""
        current_time = time.time()
        if GPIO.input(BUTTON_GPIO) == GPIO.HIGH:  # Button pressed
            if current_time - self.last_button_time > DEBOUNCE_TIME:
                if not self.button_pressed:  # Only trigger on new press
                    self.button_pressed = True
                    self.last_button_time = current_time
                    return True
        else:
            # Button released - reset pressed state
            self.button_pressed = False
        return False
            
    def clear_strip(self, strip):
        """Turn off all LEDs on a strip"""
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()
        
    def color_wipe(self, strip, color):
        """Wipe a color across the strip"""
        for i in range(strip.numPixels()):
            if not self.running:  # Check for exit
                return False
            
            # Check button state (polling)
            if self.check_button():  # Check for strip switch
                print(f"🔄 Button pressed! Switching strips...")
                self.switch_strip()
                return True
                
            strip.setPixelColor(i, color)
            strip.show()
            time.sleep(WIPE_DELAY)
        return False  # Completed without interruption
        
    def get_active_strip(self):
        """Get the currently active strip and its name"""
        if self.current_strip == 0:
            return self.strip1, "Strip 1 (GPIO18)"
        else:
            return self.strip2, "Strip 2 (GPIO21)"
            
    def get_inactive_strip(self):
        """Get the currently inactive strip"""
        if self.current_strip == 0:
            return self.strip2
        else:
            return self.strip1
    
    def switch_strip(self):
        """Switch to the other strip"""
        # Clear current strip
        active_strip, _ = self.get_active_strip()
        self.clear_strip(active_strip)
        
        # Switch to other strip
        self.current_strip = 1 - self.current_strip
        _, new_strip_name = self.get_active_strip()
        
        print(f"🔄 Switched to {new_strip_name}")
        self.button_pressed = False
        
    def run_animation(self):
        """Main animation loop"""
        color_index = 0
        
        print(f"\n🎨 Starting animation on Strip 1 (GPIO{STRIP1_GPIO})")
        print("📌 Press button to switch strips, Ctrl+C to exit")
        print("-" * 50)
        
        try:
            while self.running:
                # Get current active strip
                active_strip, strip_name = self.get_active_strip()
                current_color = COLORS[color_index]
                
                print(f"🌈 {strip_name}: Wiping color {color_index + 1}/{len(COLORS)}")
                
                # Perform color wipe
                interrupted = self.color_wipe(active_strip, current_color)
                
                if interrupted:  # Button was pressed during wipe - strip already switched
                    continue  # Skip the hold time and color advance
                
                if not self.running:  # Exit requested
                    break
                    
                # Hold the color briefly
                time.sleep(COLOR_HOLD_TIME)
                
                # Move to next color
                color_index = (color_index + 1) % len(COLORS)
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Animation stopped by user")
        
        # Automatic cleanup will happen when object is destroyed
        print("✅ LED animation completed - strips will be cleared and GPIO cleaned up automatically")
            
    def cleanup(self):
        """Optional manual cleanup for advanced users"""
        self._cleanup_gpio()
    
    def _cleanup_gpio(self):
        """Internal cleanup method - safe for automatic calling"""
        try:
            # Clear both strips
            self.clear_strip(self.strip1)
            self.clear_strip(self.strip2)
            GPIO.cleanup()
            print("✅ LED strips cleared and GPIO cleaned up")
        except Exception:
            pass  # Silent fail during destruction
    
    def __del__(self):
        """Automatic cleanup when object is destroyed"""
        self._cleanup_gpio()

def main():
    """Main function"""
    print("🎮 DUAL LED STRIP CONTROLLER WITH BUTTON")
    print("=" * 50)
    print("Hardware Setup:")
    print(f"  LED Strip 1 → GPIO{STRIP1_GPIO} (300 LEDs)")
    print(f"  LED Strip 2 → GPIO{STRIP2_GPIO} (300 LEDs)")  
    print(f"  Button → GPIO{BUTTON_GPIO} (GND when not pressed, 3.3V when pressed)")
    print("  Power & Ground → External 5V supply")
    print()
    
    # Verify user is ready
    input("📍 Press ENTER when hardware is connected...")
    
    try:
        controller = DualStripController()
        controller.run_animation()
    except Exception as e:
        print(f"❌ Error: {e}")
        # Automatic cleanup via __del__ will handle GPIO cleanup

if __name__ == "__main__":
    main()
