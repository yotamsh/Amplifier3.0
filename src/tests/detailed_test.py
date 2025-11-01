#!/usr/bin/env python3
"""
Detailed LED test - shows exactly what should happen
"""
import time
from rpi_ws281x import PixelStrip, Color

def test_strip_detailed(gpio_pin, channel, name):
    """Very detailed test with clear expectations"""
    print(f"\n🎯 DETAILED TEST: {name} (GPIO{gpio_pin})")
    print("=" * 60)
    
    try:
        strip = PixelStrip(300, gpio_pin, 800000, 10, False, 100, channel)  # Higher brightness
        strip.begin()
        print(f"✅ Strip initialized successfully")
        
        # Test 1: Single LED
        print(f"\n🔴 TEST 1: First LED should be BRIGHT RED")
        print(f"   → Look at the FIRST LED on your strip")
        print(f"   → It should be SOLID BRIGHT RED")
        print(f"   → All other LEDs should be OFF")
        
        strip.setPixelColor(0, Color(255, 0, 0))  # First LED red
        strip.show()
        input("   Press ENTER when you've checked...")
        
        # Test 2: Three LEDs
        print(f"\n🌈 TEST 2: First 3 LEDs should be RED, GREEN, BLUE")
        print(f"   → LED 0: BRIGHT RED")  
        print(f"   → LED 1: BRIGHT GREEN")
        print(f"   → LED 2: BRIGHT BLUE")
        print(f"   → All others: OFF")
        
        strip.setPixelColor(0, Color(255, 0, 0))    # Red
        strip.setPixelColor(1, Color(0, 255, 0))    # Green  
        strip.setPixelColor(2, Color(0, 0, 255))    # Blue
        strip.show()
        input("   Press ENTER when you've checked...")
        
        # Test 3: Moving dot
        print(f"\n🔵 TEST 3: Moving BLUE dot")
        print(f"   → You should see a single BLUE LED")
        print(f"   → It will move from position 0 to 9")
        print(f"   → Each position will pause 0.5 seconds")
        
        for i in range(10):
            # Clear all
            for j in range(10):
                strip.setPixelColor(j, Color(0, 0, 0))
            # Set current position
            strip.setPixelColor(i, Color(0, 0, 255))  # Blue
            strip.show()
            print(f"   → LED {i} should be BLUE (all others OFF)")
            time.sleep(0.5)
        
        # Test 4: All off
        print(f"\n⚫ TEST 4: All LEDs OFF")
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()
        print(f"   → ALL LEDs should be OFF now")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("🎯 SUPER DETAILED LED TESTING")
    print("=" * 60)
    print("This will test each strip step by step")
    print("You'll need to visually confirm each test")
    print("=" * 60)
    
    # Test GPIO 18 first
    print(f"\n🔧 Connect Strip 1 to GPIO 18 and press ENTER...")
    input()
    success1 = test_strip_detailed(18, 0, "Strip 1")
    
    if not success1:
        print("❌ Strip 1 failed - fix this before testing Strip 2")
        return
    
    # Test GPIO 19
    print(f"\n🔧 Connect Strip 2 to GPIO 19 and press ENTER...")
    input()  
    success2 = test_strip_detailed(19, 1, "Strip 2")
    
    print("\n" + "=" * 60)
    print("🎯 FINAL RESULTS:")
    print(f"   Strip 1 (GPIO 18): {'✅ WORKS' if success1 else '❌ FAILED'}")
    print(f"   Strip 2 (GPIO 19): {'✅ WORKS' if success2 else '❌ FAILED'}")
    
    if success1 and success2:
        print("\n🎉 Both strips work perfectly!")
        print("   → Your original testingLeds.py should work now")
    else:
        print("\n❌ Issues detected - please report what you saw vs expected")

if __name__ == "__main__":
    main()

