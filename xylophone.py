# This code sets up a Pico RGB Keypad Base as a xylophone using CircuitPython's synthio library.
# It features I2S audio output, additive synthesis for a metallic timbre, and dynamic LED feedback.

import math
import board
import time
import audiobusio
import synthio
import array

from pmk import PMK, number_to_xy, hsv_to_rgb
from pmk.platform.rgbkeypadbase import RGBKeypadBase as Hardware

# --- Audio Setup (I2S) ---
# Configure I2S audio output pins for the Pico.
I2S_BCLK_PIN = board.GP0
I2S_LRC_PIN = board.GP1
I2S_DIN_PIN = board.GP2

# Initialize I2S audio output and the synthio synthesizer.
audio = audiobusio.I2SOut(I2S_BCLK_PIN, I2S_LRC_PIN, I2S_DIN_PIN)
synth = synthio.Synthesizer(channel_count=1, sample_rate=44100)

# --- Envelope Definitions ---
# Envelopes define how the volume of a sound changes over time (Attack, Decay, Sustain, Release).
# Envelope for the fundamental (main) note, designed for a percussive attack and quick decay.
fundamental_envelope = synthio.Envelope(
    attack_time=0.01,
    decay_time=0.2,
    sustain_level=0.1,
    release_time=0.2,
)

# Envelope for the inharmonic overtone, even shorter and sharper for a metallic "ping."
overtone_envelope = synthio.Envelope(
    attack_time=0.01,
    decay_time=0.05,
    sustain_level=0.0,
    release_time=0.1,
)

# --- Custom Sine Waveform Generation ---
# Function to generate a 16-bit signed sine waveform, allowing for volume scaling.
def generate_sine_waveform(length=512, scale=1.0):
    waveform = array.array("h", [0] * length)
    for i in range(length):
        # Scale the sine wave amplitude directly to control volume
        waveform[i] = int(math.sin(math.pi * 2 * i / length) * (2**15 - 1) * scale)
    return waveform

# Create two sine waveforms with different volumes for additive synthesis.
active_waveform_full_volume = generate_sine_waveform(scale=1.0)
active_waveform_overtone_volume = generate_sine_waveform(scale=0.5)

# Define MIDI notes for a 16-key layout, shifted one octave higher for a xylophone range.
MIDI_NOTES = [
    48, 49, 50, 51,
    52, 53, 54, 55,
    56, 57, 58, 59,
    60, 61, 62, 63,
]

# --- Keypad Setup ---
# Initialize the Keybow library.
keybow = PMK(Hardware())

# Set maximum LED brightness and convert to a scaling factor.
MAX_LED_VALUE = 100
BRIGHTNESS_SCALING_FACTOR = MAX_LED_VALUE / 255.0

keys = keybow.keys # Get access to individual key objects

# Variables to manage LED states and active notes.
static_key_colors = [None] * 16 # Stores the base rainbow color for each key
active_notes = {}              # Tracks which notes are currently playing for each key
prev_key_states = [False] * 16 # Stores the previous pressed state of each key for edge detection

# Function to set a static rainbow color pattern across the keypad LEDs.
def set_static_rainbow_colors():
    for i in range(16):
        x, y = number_to_xy(i)
        hue = (x + y) / 6.0
        hue = hue - math.floor(hue) # Normalize hue to 0-1 range
        r, g, b = hsv_to_rgb(hue, 1, BRIGHTNESS_SCALING_FACTOR)
        keys[i].set_led(r, g, b)
        static_key_colors[i] = (r, g, b)

set_static_rainbow_colors() # Apply initial rainbow colors
keybow.update()             # Update the physical LEDs

print("Pico RGB Keypad Base project started! (Using I2S Audio with Synthio)")

audio.play(synth) # Start the synthesizer playing audio

# --- Main Loop ---
# Continuously check key states and update LEDs and audio.
while True:
    keybow.update() # Read the current state of the keypad

    for key_index in range(16):
        key = keys[key_index]
        current_pressed_state = key.pressed
        previous_pressed_state = prev_key_states[key_index]

        # Handle Key Press (detecting a *new* press event)
        if current_pressed_state and not previous_pressed_state:
            print(f"\n--- Key {key_index} pressed! ---")
            if key_index < len(MIDI_NOTES):
                key.set_led(255, 255, 255) # Set LED to white when pressed

                midi_note = MIDI_NOTES[key_index]
                # Calculate the frequency for the MIDI note
                note_frequency = 440 * (2**((midi_note - 69) / 12))

                # Create the fundamental note using the full volume sine waveform
                note_fundamental = synthio.Note(
                    frequency=note_frequency,
                    waveform=active_waveform_full_volume,
                    envelope=fundamental_envelope,
                )

                # Create the first inharmonic overtone, using a specific frequency ratio and scaled waveform
                note_overtone1 = synthio.Note(
                    frequency=note_frequency * 2.756, # Inharmonic ratio for metallic sound
                    waveform=active_waveform_overtone_volume, # Use the quieter overtone waveform
                    envelope=overtone_envelope,
                )

                # Combine both notes into a list to be played simultaneously
                notes_to_play = [note_fundamental, note_overtone1]

                # Release any previously playing notes for this key to prevent overlapping sounds
                if key_index in active_notes:
                    synth.release(active_notes[key_index])
                
                synth.press(notes_to_play) # Play the combined notes
                active_notes[key_index] = notes_to_play # Store the notes being played for this key

                print(f"Playing MIDI note {midi_note} (Key {key_index}), frequency {note_frequency:.2f} Hz")
            else:
                print(f"No MIDI note defined for key {key_index}.")

        # Handle Key Release (detecting when a key is no longer pressed)
        elif not current_pressed_state and previous_pressed_state:
            print(f"--- Key {key_index} released! ---")
            # Return LED to its static rainbow color
            r, g, b = static_key_colors[key_index]
            key.set_led(r, g, b)

            # Release the notes associated with this key
            if key_index in active_notes:
                synth.release(active_notes[key_index])
                del active_notes[key_index] # Remove from active notes tracking
                print(f"Note released for Key {key_index}")

        prev_key_states[key_index] = current_pressed_state # Update the previous state for the next loop iteration

    time.sleep(0.01) # Short delay to prevent busy-looping and conserve power
