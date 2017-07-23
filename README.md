# Matrix Plays Pokemon

This will run a user-specified gameboy advance rom on `mgba` and stream
screenshots of the running game to a public room on matrix. It will also look at
that matrix room for commands to send to the game.

Discuss mpp at
[#discuss-mpp:thebeckmeyers.xyz](https://matrix.to/#/#discuss-mpp:thebeckmeyers.xyz).
Try it out at [#mpp:thebeckmeyers.xyz](https://matrix.to/#/#mpp:thebeckmeyers.xyz).

## Requirements

- `mgba` (sdl version)
- `python3`
- `xvfb`
- `pulseaudio` (don't ask)
- gba bios
- gba rom
- python requirements from `requirements.txt`

## Usage

1. Clone this repo and modify `config.json` and `registration.yaml` for your
   homeserver.
2. Add `registration.yaml` to your homeservers app-services
3. `pip3 install -r requirements.txt`
4. `gunicorn -b localhost:19050 mpp:application`

## Disclaimer

Several implementation choices for mpp were tailored to the specific
requirements of the hardware and linux distribution on which I'm running this
software. For your own use, it may be necessary to adapt this script
significantly.

In particular I had to wrestle a lot with providing `mgba` somewhere to send
audio. I chose to launch an instance of `pulseaudio` from within the python
script not because it was the best choice nor technically elegant, but because
it worked well enough with minimum fuss on my particular setup.
