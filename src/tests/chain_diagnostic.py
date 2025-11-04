#!/usr/bin/env python3
"""
Chained LED Strip Diagnostic - Test strips individually vs chained

This will help diagnose chaining issues with your 600-LED setup
(two 300-LED strips chained together).
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

# Configuration
LED_STRIP1_GPIO = 18
LED_STRIP1_DMA = 10
LED_STRIP1_CHANNEL = 0
LED_FREQ_HZ = 800000
LED_BRIGHTNESS = 26

def test_individual_strip(led_count: int, test_name: str):
    """Test a single strip configuration"""
    print(f"\n🧪 {test_name}")
    print("=" * 60)
    
    try:
        strip = PixelStripAdapter(
            led_count=led_count,
            gpio_pin=LED_STRIP1_GPIO,
            freq_hz=LED_FREQ_HZ,
            dma=LED_STRIP1_DMA,
            invert=False,
            brightness=LED_BRIGHTNESS,
            channel=LED_STRIP1_CHANNEL
        )
        
        print(f"✅ Strip initialized: {led_count} LEDs")
        
        # Clear first
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        time.sleep(0.5)
        
        # Test patterns
        patterns = [
            ("First 10 LEDs RED", 0, 10, Pixel(255, 0, 0)),
            ("Middle LEDs BLUE", led_count//2-5, led_count//2+5, Pixel(0, 0, 255)),
            ("Last 10 LEDs GREEN", led_count-10, led_count, Pixel(0, 255, 0)),
        ]
        
        for pattern_name, start, end, color in patterns:
            print(f"\n🔍 Testing: {pattern_name}")
            
            # Clear
            strip[:] = Pixel(0, 0, 0)
            strip.show()
            time.sleep(0.3)
            
            # Apply pattern
            for i in range(start, min(end, led_count)):
                strip[i] = color
            strip.show()
            
            response = input(f"   👀 Can you see {pattern_name}? (y/n): ").lower()
            if response.startswith('n'):
                print(f"   ❌ Pattern not visible - problem with LEDs {start}-{end}")
                return False
            else:
                print(f"   ✅ Pattern visible")
        
        # Final sweep test
        print(f"\n🌈 Rainbow sweep across all {led_count} LEDs...")
        for i in range(led_count):
            strip[:] = Pixel(0, 0, 0)  # Clear
            strip[i] = Pixel(50, 50, 50)  # White pixel
            if i > 0:
                strip[i-1] = Pixel(10, 0, 0)  # Red trail
            strip.show()
            time.sleep(0.01)  # Fast sweep
        
        # Clear at end
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        
        print(f"   ✅ {test_name} completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ {test_name} failed: {e}")
        return False

def test_chaining_solution():
    """Test potential solutions for chaining issues"""
    print(f"\n🔧 TESTING CHAINING SOLUTIONS")
    print("=" * 60)
    
    print("Let's try different approaches to make chaining work:")
    
    # Solution 1: Slower frequency
    print(f"\n1️⃣ Testing with slower frequency (400kHz instead of 800kHz)")
    try:
        strip = PixelStripAdapter(
            led_count=600,
            gpio_pin=LED_STRIP1_GPIO,
            freq_hz=400000,  # Slower frequency
            dma=LED_STRIP1_DMA,
            invert=False,
            brightness=LED_BRIGHTNESS,
            channel=LED_STRIP1_CHANNEL
        )
        
        # Test LEDs 590-600 (should be on second strip)
        strip[:] = Pixel(0, 0, 0)
        for i in range(590, 600):
            strip[i] = Pixel(0, 255, 0)  # Green
        strip.show()
        
        response = input("   👀 Can you see green LEDs at positions 590-600? (y/n): ").lower()
        if response.startswith('y'):
            print("   ✅ Slower frequency works! Try updating your config.")
            return True
        else:
            print("   ❌ Slower frequency didn't help")
            
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        
    except Exception as e:
        print(f"   ❌ Slower frequency test failed: {e}")
    
    # Solution 2: Lower brightness
    print(f"\n2️⃣ Testing with very low brightness (brightness=5)")
    try:
        strip = PixelStripAdapter(
            led_count=600,
            gpio_pin=LED_STRIP1_GPIO,
            freq_hz=LED_FREQ_HZ,
            dma=LED_STRIP1_DMA,
            invert=False,
            brightness=5,  # Very low brightness
            channel=LED_STRIP1_CHANNEL
        )
        
        # Light up second strip area
        strip[:] = Pixel(0, 0, 0)
        for i in range(300, 600):
            strip[i] = Pixel(255, 255, 255)  # White on second strip
        strip.show()
        
        response = input("   👀 Can you see white LEDs on the second strip? (y/n): ").lower()
        if response.startswith('y'):
            print("   ✅ Lower brightness works! Power/signal issue confirmed.")
            return True
        else:
            print("   ❌ Lower brightness didn't help")
            
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        
    except Exception as e:
        print(f"   ❌ Lower brightness test failed: {e}")
    
    return False

def main():
    print("🔗 CHAINED LED STRIP DIAGNOSTIC")
    print("=" * 50)
    print("Hardware: Two 300-LED strips chained together")
    print("Goal: Diagnose why only first 300 LEDs work")
    print("")
    print("Connection should be:")
    print("  Pi GPIO18 → Strip1 Data-In")
    print("  Strip1 Data-Out → Strip2 Data-In") 
    print("  Both strips share 5V and GND")
    print("")
    
    # Test 1: First strip only (300 LEDs)
    success_300 = test_individual_strip(300, "TEST 1: First Strip Only (300 LEDs)")
    
    if not success_300:
        print("\n❌ First strip has issues - fix this before testing chaining")
        return
    
    input("\nPress Enter to test chained configuration...")
    
    # Test 2: Both strips chained (600 LEDs) 
    success_600 = test_individual_strip(600, "TEST 2: Both Strips Chained (600 LEDs)")
    
    if success_600:
        print("\n🎉 Chaining works perfectly!")
        return
    
    # Test 3: Try solutions
    input("\nPress Enter to test potential solutions...")
    solution_worked = test_chaining_solution()
    
    if not solution_worked:
        print(f"\n🔧 TROUBLESHOOTING SUGGESTIONS:")
        print("=" * 50)
        print("1. Check physical connection between strips:")
        print("   • Strip1 Data-Out → Strip2 Data-In")  
        print("   • Clean, solid solder joints")
        print("   • Short connecting wires (< 10cm)")
        print("")
        print("2. Power supply check:")
        print("   • Sufficient amperage (10A+ for 600 LEDs)")
        print("   • Good ground connection")
        print("   • Voltage stable under load")
        print("")
        print("3. Signal integrity:")
        print("   • Try 3.3V → 5V level shifter")
        print("   • Add 330Ω resistor on data line") 
        print("   • Shorter total cable length")
        print("")
        print("4. Alternative: Use two separate GPIO pins")
        print("   • Strip1 on GPIO18 (300 LEDs)")
        print("   • Strip2 on GPIO21 (300 LEDs)") 
        print("   • Control independently")

if __name__ == "__main__":
    main()
