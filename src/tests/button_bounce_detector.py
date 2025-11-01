#!/usr/bin/env python3
"""
Button Bounce Detection Script
- Samples GPIO 25 at fastest possible rate to detect button bounce
- Logs all state transitions with precise timestamps
- Use to determine if hardware debouncing is needed

Hardware Setup:
- SPDT Button: Common → GPIO 25, NC → GND, NO → 3.3V
- 330Ω resistor in series with GPIO 25
- 100nF capacitor from GPIO 25 to GND
- Long wire support with no floating states
"""
import sys
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("⚠️  RPi.GPIO not available - this script is for Raspberry Pi only")
    sys.exit(1)

# Configuration
BUTTON_GPIO = 25        # GPIO pin for button input
SAMPLE_INTERVAL = 0     # Fastest possible sampling rate

class ButtonBounceDetector:
    """Fastest-possible button state monitor for bounce detection"""
    
    def __init__(self):
        self.running = True
        self.transition_count = 0
        self.start_time = None
        
        print(f"🔲 Setting up button bounce detector on GPIO{BUTTON_GPIO}...")
        self.setup_gpio()
        
        print("✅ Button bounce detector initialized")
        print(f"   GPIO: {BUTTON_GPIO} (no internal pull resistors)")
        print(f"   Sampling: Fastest possible rate (no delay)")
        print()
        
    def setup_gpio(self):
        """Setup GPIO for button input with no internal pull resistors"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
            print(f"✅ GPIO{BUTTON_GPIO} configured (input, no pulls - SPDT circuit)")
            
        except Exception as e:
            print(f"❌ GPIO setup failed on GPIO{BUTTON_GPIO}: {e}")
            print(f"💡 Detailed error: {type(e).__name__}")
            raise
    
    def get_elapsed_time(self):
        """Get elapsed time since start in seconds"""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
    
    def log_transition(self, new_state, old_state):
        """Log a state transition with timestamp"""
        self.transition_count += 1
        elapsed = self.get_elapsed_time()
        
        if new_state == GPIO.HIGH:
            print(f"[{elapsed:7.3f}s] #{self.transition_count:3d} PRESSED   (0→1)")
        else:
            print(f"[{elapsed:7.3f}s] #{self.transition_count:3d} RELEASED  (1→0)")
    
    def run_detection(self):
        """Main detection loop - sample GPIO every 5ms"""
        print("🎮 BUTTON BOUNCE DETECTOR")
        print("=" * 40)
        print("Hardware Setup (SPDT Button):")
        print(f"  Button Common → GPIO{BUTTON_GPIO}")
        print(f"  Button NC     → GND")  
        print(f"  Button NO     → 3.3V")
        print(f"  330Ω + 100nF filter on GPIO{BUTTON_GPIO}")
        print()
        
        print("📊 Instructions:")
        print("  1. Press button and watch for multiple transitions")
        print("  2. Press Ctrl+C to stop")
        print()
        
        # Get initial state
        previous_state = GPIO.input(BUTTON_GPIO)
        initial_state = "PRESSED" if previous_state else "RELEASED"
        
        print(f"⌨️  Initial button state: {initial_state}")
        print("⏱️  Starting detection...")
        print()
        print("Time      #   Event      Transition")
        print("-" * 40)
        
        self.start_time = time.time()
        
        try:
            while self.running:
                current_state = GPIO.input(BUTTON_GPIO)
                
                # Check for state change
                if current_state != previous_state:
                    self.log_transition(current_state, previous_state)
                    previous_state = current_state
                
                # Wait for next sample (0 = fastest possible)
                if SAMPLE_INTERVAL > 0:
                    time.sleep(SAMPLE_INTERVAL)
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Detection stopped by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up GPIO resources"""
        print("🔄 Cleaning up...")
        self.running = False
        
        # Cleanup GPIO
        GPIO.cleanup()
        
        print("✅ GPIO cleaned up")

def main():
    """Main function"""
    print("🔌 HARDWARE SETUP CHECK:")
    print(f"   SPDT Button Common → GPIO{BUTTON_GPIO}")
    print("   SPDT Button NC → GND")
    print("   SPDT Button NO → 3.3V")
    print("   330Ω resistor + 100nF cap on GPIO line")
    print()
    
    # Verify user is ready
    input("📍 Press ENTER when button is connected...")
    print()
    
    try:
        detector = ButtonBounceDetector()
        detector.run_detection()
    except Exception as e:
        print(f"❌ Error: {e}")
        # Emergency cleanup
        try:
            GPIO.cleanup()
        except:
            pass

if __name__ == "__main__":
    main()
