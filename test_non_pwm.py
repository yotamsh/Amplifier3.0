#!/usr/bin/env python3
"""
Test script to demonstrate what happens when using non-PWM pins
"""
import time
from rpi_ws281x import PixelStrip, Color

# Test different pins
test_pins = [
    {"pin": 18, "name": "GPIO18 (PWM)", "channel": 0},  # Should work
    {"pin": 23, "name": "GPIO23 (Non-PWM)", "channel": 0},  # Should fail
    {"pin": 24, "name": "GPIO24 (Non-PWM)", "channel": 0},  # Should fail
]

def test_pin(pin_info):
    print(f"\n--- Testing {pin_info['name']} ---")
    
    try:
        strip = PixelStrip(
            30,  # Small number for testing
            pin_info['pin'], 
            800000, 
            10, 
            False, 
            50, 
            pin_info['channel']
        )
        
        strip.begin()
        print(f"✅ SUCCESS: {pin_info['name']} initialized successfully!")
        
        # Try to set a color
        strip.setPixelColor(0, Color(255, 0, 0))
        strip.show()
        print(f"✅ SUCCESS: Color set on {pin_info['name']}")
        
        # Clean up
        strip.setPixelColor(0, Color(0, 0, 0))
        strip.show()
        
    except Exception as e:
        print(f"❌ FAILED: {pin_info['name']} - {str(e)}")

if __name__ == "__main__":
    print("Testing WS2812B on different GPIO pins...")
    
    for pin_config in test_pins:
        test_pin(pin_config)
        time.sleep(1)
    
    print("\n--- Test Complete ---")
    print("Only PWM-capable pins should work with rpi-ws281x!")

