# pico-RGB-speaker-project aka SoundMeister3000
This project is for my baby boy, using a Raspberry Pi Pico, a Pimoroni RGB keypad, a small amp and speaker to create an interactive toy for him without a screen.
I am recording sounds and his first words to then put them on the Pico for playback when a button is pressed.
#
I am really terrible at coding, have always been and I have never put the time and effort in to master any programming language. Python is actually the only language that I ever dabbled in. This project is no different when it comes to previous coding, meaning I create pure Frankenstein code, this time might have been actually worse than ever before because I pretty much completely relied on Google's Gemini AI for writing my code. The final result works in the sense that my CircuitPython scripts do what I want but I am not sure that it's a very clean, concise or efficient way of doing it. Furthermore, Gemini quite a few times led me astray and hallucinated pieces of code together that had nothing to do with the packages I am using and that although I had shared very specific code examples and documentation.

AI generated project description; reading hallucinations at your own risk!

## Pico RGB Keypad Audio Player

This project transforms a Raspberry Pi Pico and the Pimoroni Pico RGB Keypad Base into a versatile soundboard, perfect for custom sound effects, musical notes, or a fun toy! It leverages the Pico's I2S capabilities for (high-quality???) audio playback and features a vibrant, static rainbow LED display with key-press feedback.
#

**Objectives**


- Create an interactive audio player: Play different MP3 files assigned to each of the 16 keys.
- Implement interruptible audio: Allow new audio files to interrupt currently playing ones, ensuring a responsive user experience.
- Develop a dynamic visual interface: Display a static rainbow LED pattern on the keypad and provide visual feedback (blinking) when a key is pressed.
- Utilize 3D-printed enclosures: Design and incorporate custom 3D-printed parts for a complete, durable, and aesthetically pleasing housing.
#

**Challenges**

- Identifying and Overcoming Geminis hallucinations when creating code for me.
- Seamless Audio Playback: Initially, using a PWM amplifier resulted in significant noise and hissing. Switching to an I2S amplifier (MAX98357A) provided much cleaner audio.
- LED Brightness Control: LEDs were way to bright for my taste, so implementation of a brightness scaling factor.
- Code Optimization for Responsiveness: The main loop was designed to be non-blocking, allowing continuous monitoring of key presses even during audio playback.
#

**Hardware Used**
- [Raspberry Pi Pico 1](https://www.raspberrypi.com/products/raspberry-pi-pico/): The heart of the project, providing the processing power and I2S audio capabilities.
- [Pimoroni Pico RGB Keypad Bas](https://shop.pimoroni.com/products/pico-rgb-keypad-base)e: The 4x4 RGB keypad providing the tactile input and visual output.
- [Adafruit I2S 3W Class D Amplifier Breakout - MAX98357A](https://www.adafruit.com/product/3006)): This amplifier significantly improved audio quality by leveraging the Pico's I2S output.
- [Pimoroni Mini Speaker 4Ω (3W)](https://shop.pimoroni.com/products/mini-speaker-4-3w?variant=2976551927818): A compact speaker suitable for this project.
#

**Project Files**
- CircuitPython Code: See the code.py file in this repository for the full CircuitPython implementation. This is my initial code used to play some .mp3 audio files.
- 3D Printable Housing: Link to my public Onshape document!
