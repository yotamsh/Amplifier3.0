#!/usr/bin/env python3
"""
LED Count Diagnostic Test - Test actual LED strip capacity

This script will help diagnose why only 300 LEDs are lighting up
instead of the configured 600 LEDs.
"""
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from led_system import PixelStripAdapter, Pixel
    import RPi.GPIO as GPIO
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this on a Raspberry Pi with required libraries installed")
    sys.exit(1)

# Configuration for Strip 1 (Rainbow strip)
LED_STRIP1_GPIO = 18
LED_STRIP1_DMA = 10
LED_STRIP1_CHANNEL = 0
LED_FREQ_HZ = 800000
LED_BRIGHTNESS = 26

def test_led_count(target_count: int):
    """Test if we can actually control the specified number of LEDs"""
    print(f"🧪 Testing {target_count} LEDs on GPIO{LED_STRIP1_GPIO}")
    print("=" * 50)
    
    try:
        # Initialize strip with target count
        strip = PixelStripAdapter(
            led_count=target_count,
            gpio_pin=LED_STRIP1_GPIO,
            freq_hz=LED_FREQ_HZ,
            dma=LED_STRIP1_DMA,
            invert=False,
            brightness=LED_BRIGHTNESS,
            channel=LED_STRIP1_CHANNEL
        )
        
        print(f"✅ Strip initialized with {target_count} LEDs")
        print(f"✅ Strip reports {strip.num_pixels()} pixels")
        
        # Clear all LEDs first
        print("🔄 Clearing all LEDs...")
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        time.sleep(1)
        
        # Test patterns to see what actually lights up
        patterns = [
            ("First 10 LEDs RED", lambda: light_range(strip, 0, 10, Pixel(255, 0, 0))),
            ("LEDs 290-310 BLUE", lambda: light_range(strip, 290, 310, Pixel(0, 0, 255))),
            ("LEDs 590-600 GREEN", lambda: light_range(strip, 590, 600, Pixel(0, 255, 0))),
            ("All LEDs DIM WHITE", lambda: light_all(strip, Pixel(10, 10, 10))),
        ]
        
        for name, pattern_func in patterns:
            print(f"\n🔍 Testing: {name}")
            strip[:] = Pixel(0, 0, 0)  # Clear first
            strip.show()
            time.sleep(0.5)
            
            try:
                pattern_func()
                strip.show()
                print(f"   ✅ Pattern applied - check your LEDs!")
                input(f"   👀 Can you see the {name}? Press Enter to continue...")
            except Exception as e:
                print(f"   ❌ Pattern failed: {e}")
        
        # Final test - count how many actually light up
        print(f"\n🔍 Final Test: Lighting up LEDs one by one")
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        time.sleep(1)
        
        # Light up LEDs gradually to see where it stops working
        ranges_to_test = [100, 200, 300, 400, 500, 600]
        for count in ranges_to_test:
            if count > target_count:
                continue
                
            print(f"   Testing first {count} LEDs...")
            for i in range(count):
                strip[i] = Pixel(0, 10, 0)  # Dim green
            strip.show()
            
            response = input(f"   👀 Can you see {count} LEDs lit? (y/n): ").lower()
            if response.startswith('n'):
                print(f"   ❌ Only working up to {count-100 if count > 100 else 0} LEDs")
                break
            elif response.startswith('y'):
                print(f"   ✅ {count} LEDs working")
                if count == target_count:
                    print(f"   🎉 All {target_count} LEDs are working!")
        
        # Clear at end
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"   This might indicate a hardware or power issue")

def light_range(strip, start: int, end: int, color: Pixel):
    """Light up a range of LEDs"""
    for i in range(start, min(end, strip.num_pixels())):
        strip[i] = color

def light_all(strip, color: Pixel):
    """Light up all LEDs"""
    strip[:] = color

def main():
    print("🧪 LED STRIP COUNT DIAGNOSTIC")
    print("=" * 40)
    print("This test will help determine why only 300 LEDs")
    print("are lighting up instead of 600.")
    print()
    print("⚠️  Make sure your power supply can handle the load!")
    print("⚠️  600 LEDs at full brightness = ~36A")
    print("⚠️  We're using dim settings for safety")
    print()
    
    # Test different counts
    counts_to_test = [300, 600]
    
    for count in counts_to_test:
        test_led_count(count)
        print()
        if count < max(counts_to_test):
            input(f"Press Enter to test with {counts_to_test[counts_to_test.index(count)+1]} LEDs...")
    
    print("🏁 Diagnostic complete!")
    print()
    print("💡 Common issues:")
    print("   • Power supply too weak (need 10A+ for 600 LEDs)")
    print("   • LED strip physically only has 300 LEDs")
    print("   • Need to chain two 300-LED strips together")  
    print("   • Data signal degradation over long strips")
    print("   • Library limitations")

if __name__ == "__main__":
    main()
