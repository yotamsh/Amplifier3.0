#!/usr/bin/env python3
"""
Test dual strips with sequential updates (not simultaneous)
"""
import time
from rpi_ws281x import PixelStrip, Color

def test_sequential_updates():
    """Test updating strips one at a time instead of simultaneously"""
    
    print("🎯 SEQUENTIAL UPDATE TEST")
    print("=" * 50)
    print("This tests updating strips ONE AT A TIME to avoid interference")
    print()
    
    # Use your working individual GPIO pins
    gpio1 = int(input("Enter GPIO for Strip 1 (that worked individually): "))
    gpio2 = int(input("Enter GPIO for Strip 2 (that worked individually): "))
    
    print(f"\n🔌 Connect strips:")
    print(f"   Strip 1 → GPIO {gpio1}")  
    print(f"   Strip 2 → GPIO {gpio2}")
    input("Press ENTER when connected...")
    
    try:
        # Create strips with different DMA channels
        strip1 = PixelStrip(10, gpio1, 800000, 10, False, 100, 0)
        strip2 = PixelStrip(10, gpio2, 800000, 11, False, 100, 1)  # Different channel
        
        strip1.begin()
        strip2.begin()
        
        print("✅ Both strips initialized")
        
        # Test 1: Sequential color setting
        print("\n🎨 TEST 1: Sequential Updates")
        print("Setting Strip 1 to RED...")
        
        # Update Strip 1
        for i in range(5):
            strip1.setPixelColor(i, Color(255, 0, 0))  # Red
        strip1.show()
        time.sleep(0.1)  # Small delay
        
        print("Setting Strip 2 to BLUE...")
        
        # Update Strip 2 (separately)
        for i in range(5):
            strip2.setPixelColor(i, Color(0, 0, 255))  # Blue
        strip2.show()
        time.sleep(0.1)
        
        print("\n👀 CHECK: Strip 1 RED, Strip 2 BLUE?")
        result1 = input("Are colors correct and stable? (y/n): ").strip().lower()
        
        if result1 == 'y':
            print("✅ Sequential updates work!")
            
            # Test 2: Alternating animation
            print("\n🎨 TEST 2: Alternating Animation")
            print("Watch for smooth color changes...")
            
            colors = [
                (Color(255, 0, 0), Color(0, 255, 0)),    # Red vs Green
                (Color(0, 0, 255), Color(255, 255, 0)),  # Blue vs Yellow
                (Color(255, 0, 255), Color(0, 255, 255)) # Magenta vs Cyan
            ]
            
            for color1, color2 in colors:
                # Update strip 1
                for i in range(5):
                    strip1.setPixelColor(i, color1)
                strip1.show()
                time.sleep(0.05)  # Slight delay
                
                # Update strip 2
                for i in range(5):
                    strip2.setPixelColor(i, color2)
                strip2.show()
                time.sleep(1)
            
            print("Animation completed!")
            result2 = input("Did the animation work smoothly? (y/n): ").strip().lower()
            
            return result1 == 'y' and result2 == 'y'
        else:
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    finally:
        # Turn off all LEDs
        try:
            for i in range(10):
                strip1.setPixelColor(i, Color(0, 0, 0))
                strip2.setPixelColor(i, Color(0, 0, 0))
            strip1.show()
            strip2.show()
        except:
            pass

def main():
    print("🔧 DUAL STRIP SEQUENTIAL UPDATE TEST")
    print("=" * 50)
    print("Since individual strips work, let's test sequential updates")
    print("to avoid simultaneous interference")
    
    success = test_sequential_updates()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Sequential updates work!")
        print("Solution: Update strips one at a time, not simultaneously")
    else:
        print("❌ Sequential updates still have issues")
        print("Need to try other solutions (power, grounding, etc.)")

if __name__ == "__main__":
    main()

