#!/usr/bin/env python3
"""
Audio test script for Raspberry Pi USB audio setup
Tests pygame audio playback using an MP3 file
"""
import pygame
import time
import os
import sys

def test_audio():
    """Test audio playback using pygame"""
    
    # Audio file path
    mp3_file = "./songs/testS.mp3"
    
    print("🎵 USB Audio Test Script")
    print("=" * 40)
    
    # Check if file exists
    if not os.path.exists(mp3_file):
        print(f"❌ ERROR: MP3 file not found: {mp3_file}")
        print("Make sure the songs folder and testS.mp3 file exist")
        return False
    
    print(f"✅ Found MP3 file: {mp3_file}")
    
    try:
        # Initialize pygame mixer
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        
        print(f"✅ Pygame mixer initialized: {pygame.mixer.get_init()}")
        print("   (This should show USB audio device if configured correctly)")
        
        # Load the MP3 file
        print(f"\n🔄 Loading MP3 file...")
        pygame.mixer.music.load(mp3_file)
        print("✅ MP3 file loaded successfully")
        
        # Play the music
        print("\n🔊 Playing audio...")
        print("   Listen for sound from your USB-connected speaker!")
        print("   Press Ctrl+C to stop playback early")
        
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        start_time = time.time()
        while pygame.mixer.music.get_busy():
            elapsed = time.time() - start_time
            print(f"\r   Playing... {elapsed:.1f}s", end="", flush=True)
            time.sleep(0.1)
        
        print(f"\n✅ Audio playback completed!")
        
        return True
        
    except pygame.error as e:
        print(f"❌ Pygame error: {e}")
        print("This might indicate an audio configuration issue")
        return False
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Playback stopped by user")
        pygame.mixer.music.stop()
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
        
    finally:
        if pygame.mixer.get_init():
            pygame.mixer.quit()
            print("🔄 Pygame mixer closed")

def main():
    """Main function"""
    print("Starting USB Audio Test...")
    print("Make sure your USB audio adapter is connected")
    print("and your speaker/headphones are plugged in!")
    print()
    
    success = test_audio()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Audio test completed!")
        print("If you heard the music, your USB audio setup is working correctly.")
    else:
        print("❌ Audio test failed!")
        print("Check your USB audio adapter connection and configuration.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

