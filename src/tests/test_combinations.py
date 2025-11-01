#!/usr/bin/env python3
"""
Systematic test of GPIO pin combinations for dual LED strips
"""
import time
from rpi_ws281x import PixelStrip, Color

def get_physical_pin(gpio):
    """Convert GPIO number to physical pin number"""
    gpio_to_pin = {
        12: 32,
        13: 33, 
        18: 12,
        19: 35
    }
    return gpio_to_pin.get(gpio, "?")

# Test combinations: (gpio1, channel1, gpio2, channel2, description)
test_combinations = [
    (18, 0, 12, 0, "GPIO 18 + GPIO 12 (both PWM0)"),
    (18, 0, 19, 1, "GPIO 18 + GPIO 19 (PWM0 + PWM1)"), 
    (12, 0, 13, 1, "GPIO 12 + GPIO 13 (PWM0 + PWM1)"),
    (18, 0, 13, 1, "GPIO 18 + GPIO 13 (PWM0 + PWM1)"),
]

def test_combination(gpio1, chan1, gpio2, chan2, desc):
    """Test a specific GPIO pin combination"""
    print(f"\n🧪 TESTING: {desc}")
    print("-" * 60)
    
    # Connection instructions
    print(f"🔌 CONNECT YOUR LED STRIPS:")
    print(f"   Strip 1 data wire → GPIO {gpio1} (Physical pin {get_physical_pin(gpio1)})")
    print(f"   Strip 2 data wire → GPIO {gpio2} (Physical pin {get_physical_pin(gpio2)})")
    print(f"   Keep power and ground connected as before")
    print()
    input("📍 Press ENTER when strips are connected to the correct GPIOs...")
    print()
    
    try:
        # Create both strips
        strip1 = PixelStrip(10, gpio1, 800000, 10, False, 100, chan1)  # Only 10 LEDs for testing
        strip2 = PixelStrip(10, gpio2, 800000, 11, False, 100, chan2)
        
        strip1.begin()
        strip2.begin()
        print("✅ Both strips initialized")
        
        # Test 1: Different colors on each strip
        print(f"🔴 Strip 1 (GPIO {gpio1}): RED")
        print(f"🔵 Strip 2 (GPIO {gpio2}): BLUE")
        
        for i in range(5):  # First 5 LEDs
            strip1.setPixelColor(i, Color(255, 0, 0))  # Red
            strip2.setPixelColor(i, Color(0, 0, 255))  # Blue
            
        strip1.show()
        strip2.show()
        
        print("👀 CHECK: Do you see stable RED on strip 1, stable BLUE on strip 2?")
        result = input("   Enter (g)ood, (f)licker, or (o)ff: ").lower().strip()
        
        # Turn off
        for i in range(10):
            strip1.setPixelColor(i, Color(0, 0, 0))
            strip2.setPixelColor(i, Color(0, 0, 0))
        strip1.show()
        strip2.show()
        
        return result == 'g'
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("🎯 SYSTEMATIC GPIO PIN COMBINATION TESTING")
    print("=" * 60)
    print("This will test 4 different GPIO pin combinations to find the best one")
    print("For each test, you'll need to:")
    print("  1. Connect LED strips to the specified GPIO pins")
    print("  2. Visually check if LEDs work properly") 
    print("  3. Report: (g)ood, (f)licker, or (o)ff")
    print()
    print("Make sure your LED strips are powered externally!")
    print("=" * 60)
    input("📍 Press ENTER when ready to start testing...")
    
    results = {}
    
    for gpio1, chan1, gpio2, chan2, desc in test_combinations:
        success = test_combination(gpio1, chan1, gpio2, chan2, desc)
        results[desc] = success
        
        if success:
            print(f"✅ {desc} - WORKS!")
        else:
            print(f"❌ {desc} - FAILED")
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("🏆 FINAL RESULTS:")
    
    working_combinations = []
    for desc, success in results.items():
        status = "✅ WORKS" if success else "❌ FAILED"
        print(f"   {status}: {desc}")
        if success:
            working_combinations.append(desc)
    
    print(f"\n🎯 WORKING COMBINATIONS: {len(working_combinations)}")
    
    if working_combinations:
        print(f"🎉 USE THIS: {working_combinations[0]}")
    else:
        print("❌ No combinations worked - check hardware connections")

if __name__ == "__main__":
    main()
