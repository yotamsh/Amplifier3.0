#!/usr/bin/env python3
"""
Test script using neopixel library for WS2812B LED control
Simple test: Red fill -> Green wipe animation
"""

import time
import board
import neopixel

# ===== CONFIGURATION PARAMETERS (Modify these as needed) =====
LED_COUNT = 300              # Number of LEDs on the strip
LED_PIN = board.D23          # GPIO pin (DX = GPIO X)
BRIGHTNESS = 0.1             # 10% brightness (0.0 to 1.0)
WIPE_DELAY_MS = 5           # Delay between pixels during wipe (milliseconds)

# Colors (R, G, B) values 0-255
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_OFF = (0, 0, 0)

# Animation timing
HOLD_TIME = 2.0             # How long to hold red color (seconds)
# ==============================================================

def main():
    print("🎮 NeoPixel LED Test Starting!")
    print(f"   Strip: {LED_COUNT} LEDs")
    print(f"   GPIO: {LED_PIN}")
    print(f"   Brightness: {int(BRIGHTNESS * 100)}%")
    print(f"   Wipe delay: {WIPE_DELAY_MS}ms per pixel")
    
    try:
        # Initialize the LED strip
        print("\n🔧 Initializing LED strip...")
        pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, brightness=BRIGHTNESS, auto_write=False)
        print("✅ LED strip initialized successfully!")
        
        print(f"\n🔴 Phase 1: Fill all {LED_COUNT} LEDs with RED")
        # Fill entire strip with red
        pixels.fill(COLOR_RED)
        pixels.show()
        
        # Hold red for specified time
        print(f"   → Holding red for {HOLD_TIME} seconds...")
        time.sleep(HOLD_TIME)
        
        print(f"\n🟢 Phase 2: Fast wipe to GREEN (delay: {WIPE_DELAY_MS}ms)")
        # Wipe from red to green pixel by pixel
        wipe_delay = WIPE_DELAY_MS / 1000.0  # Convert to seconds
        
        for i in range(LED_COUNT):
            pixels[i] = COLOR_GREEN
            pixels.show()
            time.sleep(wipe_delay)
            
            # Progress indicator every 50 pixels
            if (i + 1) % 50 == 0:
                print(f"   → Progress: {i + 1}/{LED_COUNT} pixels")
        
        print("✅ Green wipe completed!")
        
        # Hold green briefly
        print("\n⏸️  Holding green for 2 seconds...")
        time.sleep(2.0)
        
        # Turn off all LEDs
        print("\n⚫ Turning off all LEDs...")
        pixels.fill(COLOR_OFF)
        pixels.show()
        print("✅ All LEDs turned off")
        
        print("\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("💡 Troubleshooting tips:")
        print("   - Make sure to run with: sudo python3 test_neopixel.py")
        print("   - Check that GPIO 18 is connected to LED strip DIN")
        print("   - Verify power supply is adequate for 300 LEDs")
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Test interrupted by user")
        # Clean up - turn off all LEDs
        try:
            pixels.fill(COLOR_OFF)
            pixels.show()
            print("✅ All LEDs turned off safely")
        except:
            pass

if __name__ == "__main__":
    main()
