#!/usr/bin/env python3
"""
Strip Connection Diagnostic - Test data flow between chained strips

This specifically tests the connection between Strip1 Data-Out → Strip2 Data-In
when chained together as one 600-LED strip.
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

def test_connection_boundary():
    """Test the exact boundary where Strip1 ends and Strip2 begins"""
    print("🔗 TESTING STRIP CONNECTION BOUNDARY")
    print("=" * 50)
    print("This tests LEDs around position 300 where Strip1 → Strip2")
    print("")
    
    try:
        # Initialize as single 600-LED strip
        strip = PixelStripAdapter(
            led_count=600,
            gpio_pin=18,
            freq_hz=800000,
            dma=10,
            invert=False,
            brightness=50,  # Higher brightness for visibility
            channel=0
        )
        
        print(f"✅ 600-LED strip initialized")
        
        # Test specific boundary positions
        boundary_tests = [
            ("LEDs 295-304 (boundary crossing)", 295, 305),
            ("LED 299 only (last of Strip1)", 299, 300),
            ("LED 300 only (first of Strip2)", 300, 301),
            ("LED 301 only (second of Strip2)", 301, 302),
            ("LEDs 300-310 (Strip2 start)", 300, 311),
        ]
        
        for test_name, start, end in boundary_tests:
            print(f"\n🔍 Testing: {test_name}")
            
            # Clear all
            strip[:] = Pixel(0, 0, 0)
            strip.show()
            time.sleep(0.5)
            
            # Light up test range in bright white
            for i in range(start, end):
                strip[i] = Pixel(255, 255, 255)
            strip.show()
            
            response = input(f"   👀 Can you see LEDs {start}-{end-1}? (y/n/partial): ").lower()
            
            if response.startswith('y'):
                print(f"   ✅ All LEDs {start}-{end-1} visible")
            elif response.startswith('p'):
                visible_up_to = input(f"   📍 Which LED is the last visible one? ")
                print(f"   ⚠️  Data stops at LED {visible_up_to}")
                if int(visible_up_to) == 299:
                    print(f"   🔴 CONFIRMED: Connection broken between Strip1 and Strip2")
                    return False
            else:
                print(f"   ❌ No LEDs visible in range {start}-{end-1}")
                if start >= 300:
                    print(f"   🔴 CONFIRMED: Strip2 not receiving data")
                    return False
        
        # Final test - light up the exact transition
        print(f"\n🌈 Final test: Sliding LED across boundary...")
        for pos in range(295, 310):
            strip[:] = Pixel(0, 0, 0)
            strip[pos] = Pixel(255, 0, 0)  # Red moving dot
            strip.show()
            print(f"   LED {pos}: {'Strip1' if pos < 300 else 'Strip2'}")
            time.sleep(0.3)
        
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_data_integrity():
    """Test if data stream is getting corrupted"""
    print(f"\n📡 TESTING DATA STREAM INTEGRITY")
    print("=" * 50)
    
    try:
        strip = PixelStripAdapter(
            led_count=600,
            gpio_pin=18,
            freq_hz=800000,
            dma=10,
            invert=False,
            brightness=30,
            channel=0
        )
        
        # Test 1: Set every 10th LED to check pattern integrity
        print(f"🔍 Test 1: Every 10th LED pattern")
        strip[:] = Pixel(0, 0, 0)
        
        for i in range(0, 600, 10):
            strip[i] = Pixel(100, 100, 100)  # White dots every 10 LEDs
        strip.show()
        
        response = input("   👀 Can you see white dots every 10 LEDs throughout both strips? (y/n): ").lower()
        if response.startswith('n'):
            last_visible = input("   📍 What's the position of the last visible white dot? ")
            print(f"   ⚠️  Pattern breaks at LED {last_visible}")
        
        # Test 2: Alternating colors across boundary
        print(f"\n🔍 Test 2: Red/Blue alternating pattern")
        for i in range(600):
            if i % 2 == 0:
                strip[i] = Pixel(100, 0, 0)  # Red
            else:
                strip[i] = Pixel(0, 0, 100)  # Blue
        strip.show()
        
        response = input("   👀 Do you see red/blue alternating across both strips? (y/n): ").lower()
        if response.startswith('n'):
            print("   ❌ Alternating pattern not working - data corruption likely")
        
        # Test 3: Fill second strip completely
        print(f"\n🔍 Test 3: Second strip only (LEDs 300-599)")
        strip[:] = Pixel(0, 0, 0)
        for i in range(300, 600):
            strip[i] = Pixel(0, 255, 0)  # Green second strip
        strip.show()
        
        response = input("   👀 Is the second strip completely green? (y/n): ").lower()
        if response.startswith('n'):
            print("   🔴 CONFIRMED: Second strip not receiving data")
            return False
        else:
            print("   ✅ Second strip receiving data correctly!")
            return True
        
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        
    except Exception as e:
        print(f"❌ Data integrity test failed: {e}")
        return False

def main():
    print("🔍 STRIP CONNECTION DIAGNOSTIC")
    print("=" * 40)
    print("Hardware: Two 300-LED strips chained together")
    print("Problem: LEDs 301+ don't work, but each strip works individually")
    print("")
    print("Physical connection should be:")
    print("  Pi GPIO18 → Strip1 Data-In")
    print("  Strip1 Data-Out → Strip2 Data-In")
    print("  Strip1 5V/GND ← PSU → Strip2 5V/GND")
    print("")
    
    # Test the boundary connection
    connection_ok = test_connection_boundary()
    
    if not connection_ok:
        print(f"\n🔧 CONNECTION TROUBLESHOOTING:")
        print("=" * 50)
        print("🔴 Issue: Strip1 → Strip2 data connection broken")
        print("")
        print("Check these physical connections:")
        print("1. Strip1 Data-Out pad → Strip2 Data-In pad")
        print("   • Clean solder joints")
        print("   • No cold solder joints")
        print("   • Continuity test with multimeter")
        print("")
        print("2. Connection wire:")
        print("   • Use short wire (<10cm)")
        print("   • 22-24 AWG wire")
        print("   • Solid connection on both ends")
        print("")
        print("3. Strip orientation:")
        print("   • Check arrow direction on strips")
        print("   • Data flows: Strip1 In→Out → Strip2 In→Out")
        print("   • Both strips same orientation")
        print("")
        print("4. Test continuity:")
        print("   • Multimeter between Strip1 Data-Out and Strip2 Data-In")
        print("   • Should read near 0 ohms")
        return
    
    # If boundary test passed, check data integrity
    input("\nPress Enter to test data stream integrity...")
    
    data_ok = test_data_integrity()
    
    if data_ok:
        print(f"\n🎉 SUCCESS!")
        print("=" * 30)
        print("Both strips are working correctly!")
        print("The issue might be in your main code configuration.")
        print("")
        print("Double-check your buttonLeds_test.py:")
        print("• LED_STRIP1_COUNT = 600 ✓")
        print("• strip1 = PixelStripAdapter(led_count=600, ...) ✓")
        print("• Animation loops: range(strip.num_pixels()) ✓")
    else:
        print(f"\n🔧 NEXT STEPS:")
        print("=" * 30)
        print("1. Fix the physical connection between strips")
        print("2. Re-run this diagnostic")
        print("3. Once working, update your main code")

if __name__ == "__main__":
    main()
