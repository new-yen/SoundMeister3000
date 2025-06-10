# SPDX-FileCopyrightText: 2021 Sandy Macdonald / 2021 Kattni Rembor for Adafruit Industries
# MODIFIED FOR I2S AUDIO OUTPUT and SYNTHIO FOR XYLOPHONE SOUNDS.
# Further modified for static rainbow pattern and key press blink.
# Corrected key release detection and waveform type.
# Using synth.press() and synth.release()
# Modified envelope for longer sustain.
# Adjusted MIDI notes for one octave higher.
# Improved sound quality by increasing sample rate and waveform resolution.
# Further improved by increasing release time to smooth fade-out.
# Implemented official PMK .rotate() method for keypad orientation.
# Rotated pattern 90 degrees counter-clockwise.
# Implemented additive synthesis for a more metallic, xylophone-like timbre.
# DEBUGGED: Corrected note volume control by scaling waveforms directly, based on official synthio.Note documentation.
#
# SPDX-License-Identifier: MIT

import math
import board
import time
import audiobusio
import synthio  # Import the synthio library!
import array  # Import array to create custom waveform

from pmk import PMK, number_to_xy, hsv_to_rgb
from pmk.platform.rgbkeypadbase import RGBKeypadBase as Hardware

# --- Audio Setup (I2S) ---
I2S_BCLK_PIN = board.GP0  # Bit Clock
I2S_LRC_PIN = board.GP1  # Left-Right Clock (Word Select)
I2S_DIN_PIN = board.GP2  # Data In

audio = audiobusio.I2SOut(I2S_BCLK_PIN, I2S_LRC_PIN, I2S_DIN_PIN)
synth = synthio.Synthesizer(channel_count=1, sample_rate=44100)

# --- Envelope Definitions ---
fundamental_envelope = synthio.Envelope(
    attack_time=0.01,
    decay_time=0.2,
    sustain_level=0.1,
    release_time=0.2,
)

overtone_envelope = synthio.Envelope(
    attack_time=0.01,
    decay_time=0.05,
    sustain_level=0.0,
    release_time=0.1,
)


# --- Custom Sine Waveform Generation ---
# Modified to accept a 'scale' factor for volume
def generate_sine_waveform(length=512, scale=1.0):
    """Generates a 16-bit SIGNED sine waveform, scaled by 'scale' factor."""
    waveform = array.array("h", [0] * length)
    for i in range(length):
        # Scale the sine wave amplitude directly
        waveform[i] = int(math.sin(math.pi * 2 * i / length) * (2**15 - 1) * scale)
    return waveform

# Create two separate waveforms with different volumes
active_waveform_full_volume = generate_sine_waveform(scale=1.0) # For the fundamental
active_waveform_overtone_volume = generate_sine_waveform(scale=0.5) # For the overtone (adjust 0.5 for desired loudness)


# Define the MIDI notes for a 16-key xylophone, shifted one octave higher.
MIDI_NOTES = [
    48, 49, 50, 51,
    52, 53, 54, 55,
    56, 57, 58, 59,
    60, 61, 62, 63,
]

# --- Keypad Setup ---
keybow = PMK(Hardware())

MAX_LED_VALUE = 50
BRIGHTNESS_SCALING_FACTOR = MAX_LED_VALUE / 255.0

keys = keybow.keys

static_key_colors = [None] * 16
active_notes = {}
prev_key_states = [False] * 16

def set_static_rainbow_colors():
    for i in range(16):
        x, y = number_to_xy(i)
        hue = (x + y) / 6.0
        hue = hue - math.floor(hue)
        r, g, b = hsv_to_rgb(hue, 1, BRIGHTNESS_SCALING_FACTOR)
        keys[i].set_led(r, g, b)
        static_key_colors[i] = (r, g, b)

set_static_rainbow_colors()
keybow.update()

print("Pico RGB Keypad Base project started! (Using I2S Audio with Synthio)")

audio.play(synth)

# --- Main Loop ---
while True:
    keybow.update()

    for key_index in range(16):
        key = keys[key_index]
        current_pressed_state = key.pressed
        previous_pressed_state = prev_key_states[key_index]

        # --- Handle Key Press (detecting a *new* press) ---
        if current_pressed_state and not previous_pressed_state:
            print(f"\n--- Key {key_index} pressed! ---")
            if key_index < len(MIDI_NOTES):
                key.set_led(255, 255, 255)

                midi_note = MIDI_NOTES[key_index]
                note_frequency = 440 * (2**((midi_note - 69) / 12))

                # Create the fundamental note using the full volume waveform
                note_fundamental = synthio.Note(
                    frequency=note_frequency,
                    waveform=active_waveform_full_volume, # Use waveform scaled to full volume
                    envelope=fundamental_envelope,
                )

                # Create the first inharmonic overtone using the scaled waveform
                note_overtone1 = synthio.Note(
                    frequency=note_frequency * 2.756, # Inharmonic ratio
                    waveform=active_waveform_overtone_volume, # Use waveform scaled to 0.5 volume
                    envelope=overtone_envelope,
                )

                # Create a list containing all notes to play for this key press
                notes_to_play = [note_fundamental, note_overtone1]

                if key_index in active_notes:
                    synth.release(active_notes[key_index])
                synth.press(notes_to_play) # Press all notes in the list
                active_notes[key_index] = notes_to_play # Store the list of notes

                print(f"Playing MIDI note {midi_note} (Key {key_index}), frequency {note_frequency:.2f} Hz")
            else:
                print(f"No MIDI note defined for key {key_index}.")

        # --- Handle Key Release ---
        elif not current_pressed_state and previous_pressed_state:
            print(f"--- Key {key_index} released! ---")
            r, g, b = static_key_colors[key_index]
            key.set_led(r, g, b)

            if key_index in active_notes:
                synth.release(active_notes[key_index]) # Release all notes associated with this key
                del active_notes[key_index]
                print(f"Note released for Key {key_index}")

        prev_key_states[key_index] = current_pressed_state

    time.sleep(0.01)
