#!/usr/bin/env python3
"""
Button LED Control Script - Keyboard-controlled LED with Cbreak Mode
- Simple LED on GPIO16 controlled by keyboard input
- Press '1' to turn LED ON (3.3V) - immediate detection
- Press '0' to turn LED OFF (GND) - immediate detection
- Press 'q' to quit
- Press Ctrl+C to exit safely
"""
import sys
import time
import tty
import termios

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("⚠️  RPi.GPIO not available - this script is for Raspberry Pi only")
    sys.exit(1)

# LED Configuration
LED_GPIO = 16               # GPIO16 (Physical pin 36)

class ButtonLEDController:
    """Simple LED controller with cbreak mode keyboard input"""
    
    def __init__(self):
        self.running = True
        self.led_state = False  # False = OFF, True = ON
        
        # Setup GPIO
        print(f"🔲 Setting up LED on GPIO{LED_GPIO}...")
        self.setup_gpio()
        
        print("✅ Button LED controller initialized")
        print(f"   LED: GPIO{LED_GPIO} → Currently OFF")
        print()
        
    def setup_gpio(self):
        """Setup GPIO for LED output"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(LED_GPIO, GPIO.OUT, initial=GPIO.LOW)  # Start with LED OFF
            print(f"✅ LED configured on GPIO{LED_GPIO} (output mode)")
            
        except Exception as e:
            print(f"❌ GPIO setup failed on GPIO{LED_GPIO}: {e}")
            print(f"💡 Detailed error: {type(e).__name__}")
            raise
    
    def read_key(self):
        """Read a single keypress using cbreak mode"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)  # Set terminal to cbreak mode
            return sys.stdin.read(1).lower()  # Read single character
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)  # Restore settings
    
    def set_led(self, state):
        """Control LED state"""
        if state:
            GPIO.output(LED_GPIO, GPIO.HIGH)  # 3.3V - LED ON
            self.led_state = True
            print("🟢 LED ON  (3.3V)")
        else:
            GPIO.output(LED_GPIO, GPIO.LOW)   # GND - LED OFF
            self.led_state = False
            print("🔴 LED OFF (GND)")
    
    def display_status(self):
        """Display current status and controls"""
        status = "ON" if self.led_state else "OFF"
        voltage = "3.3V" if self.led_state else "GND"
        
        print(f"📊 Status: LED is {status} ({voltage})")
        print("📝 Controls:")
        print("   '1' → Turn LED ON")
        print("   '0' → Turn LED OFF")  
        print("   'q' → Quit")
        print("   Ctrl+C → Emergency exit")
        print()
        print("⌨️  Press a key...")
    
    def run(self):
        """Main control loop with cbreak mode"""
        print("🎮 BUTTON LED KEYBOARD CONTROLLER")
        print("=" * 40)
        print("Hardware Setup:")
        print(f"  LED + → GPIO{LED_GPIO} (Physical pin 36)")
        print(f"  LED - → Pi Ground (any GND pin)")
        print()
        
        # Initial status display
        self.display_status()
        
        try:
            while self.running:
                # Read a single key press
                key = self.read_key()
                
                # Process the key
                if key == '1':
                    if not self.led_state:
                        self.set_led(True)
                    else:
                        print("💡 LED is already ON")
                        
                elif key == '0':
                    if self.led_state:
                        self.set_led(False)
                    else:
                        print("💡 LED is already OFF")
                        
                elif key == 'q':
                    print("👋 Quit requested...")
                    self.running = False
                    break
                    
                elif key == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt
                    
                else:
                    print(f"❓ Unknown key: '{key}' - Use '1', '0', or 'q'")
                
        except KeyboardInterrupt:
            print("\n⏹️  Interrupted by Ctrl+C")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        print("🔄 Cleaning up...")
        self.running = False
        
        # Turn off LED
        GPIO.output(LED_GPIO, GPIO.LOW)
        
        # Cleanup GPIO
        GPIO.cleanup()
        
        print("✅ LED turned off and resources cleaned up")

def main():
    """Main function"""
    print("🔌 HARDWARE SETUP CHECK:")
    print(f"   Connect LED positive (long leg) → GPIO{LED_GPIO} (pin 36)")
    print("   Connect LED negative (short leg) → Pi Ground (pin 34 or 39)")
    print("   Note: No resistor needed for testing (short duration)")
    print()
    
    # Verify user is ready
    input("📍 Press ENTER when LED is connected...")
    print()
    
    try:
        controller = ButtonLEDController()
        controller.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        # Emergency cleanup
        try:
            GPIO.cleanup()
        except:
            pass

if __name__ == "__main__":
    main()