#!/usr/bin/env python3
"""Set MP3 album tag"""
import sys
import eyed3

# Suppress eyed3 verbose logging
eyed3.log.setLevel("ERROR")

if len(sys.argv) != 3:
    print("Usage: python set_album.py <song.mp3> <album_name>")
    sys.exit(1)

song_file = sys.argv[1]
album_name = sys.argv[2]

# Load MP3
audio = eyed3.load(song_file)

if audio is None or audio.tag is None:
    print(f"❌ Error: Couldn't load {song_file}")
    sys.exit(1)

# Set album
audio.tag.album = album_name
audio.tag.save()

print(f"✅ Set album to '{album_name}' for {song_file}")