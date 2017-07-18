# Matrix Plays Pokemon

This will run a user-specified gameboy advance rom on mgba and stream
screenshots of the running game to a public room on matrix. It will also look at
that matrix room for commands to send to the game.

## Requirements

- mgba
- python3
- xvfb
- pulseaudio (don't ask)
- gba bios
- gba rom

## Usage

1. Clone this repo and modify config.json and registration.yaml for your
   homeserver.
2. Add registration.yaml to your homeservers app-services
3. `pip3 install -r requirements.txt`
4. `gunicorn -b localhost:19050 mpp:application`
