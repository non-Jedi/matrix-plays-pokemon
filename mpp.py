# Copyright 2017 Adam Beckmeyer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import sys
from gyr import server, matrix_objects, exceptions
from pyvirtualdisplay.smartdisplay import SmartDisplay
from easyprocess import EasyProcess
import time
import json
from io import BytesIO

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s : %(levelname)s : %(name)s : %(message)s")
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Must start display before we can use Xlib via pynput
disp = SmartDisplay(visible=False, size=(240, 160))
disp.start()
logger.info("xvfb display started")
from pynput.keyboard import Key, Controller
logger.info("pynput imported and working")
# Have to start pulse here because mgba is being a weenie
pulse = EasyProcess("pulseaudio")
pulse.start()
logger.info("pulseaudio started")

with open("config.json") as f:
    config = json.load(f)

if config["debug"]:
    logger.setLevel(logging.DEBUG)

application = server.Application(config["hs_address"], config["token"])

class MPPServer:

    def __init__(self, application, config):
        self.config = config
        self.config["room_alias"] = ("#" + self.config["local_room_alias"] +
                                     ":" + self.config["hs_name"])
        self.config["user_id"] = ("@" + self.config["local_user_id"] +
                                  ":" + self.config["hs_name"])

        self.disp = disp
        self.keyboard = Controller()
        self.api = application.Api()

        try:
            # when creating a room with a room alias, only local part of alias is used
            self.room_id = self.api.create_room(alias=self.config["local_room_alias"],
                                                is_public=True)
            logger.info("new room created: " + self.room_id)
        except exceptions.MatrixError:
            # if it already exists just get the room_id
            self.room_id = self.api.get_room_id(self.config["room_alias"])
            logger.info("using existing room: " + self.room_id)

        self._start_mgba()

    def _start_mgba(self):
        self.pkmn = EasyProcess("mgba -s 2 -b " +
                                self.config["bios_location"] + " " +
                                self.config["rom_location"])
        self.pkmn.start()
        logger.info("mgba started")

        self.ts = time.time()
        time.sleep(5)
        self._load()
        self.send_screenshot()

    def __del__(self):
        self.pkmn.stop()
        self.disp.stop()

    def send_screenshot(self):
        if self.ts + 2 < time.time():
            self._send()
            self.ts = time.time()

    def _send(self):
        img = self.disp.grab()
        f = BytesIO()
        try:
            img.save(f, format="JPEG", quality=50, optimize=True)
            mxc = self.api.media_upload(f.getvalue(), "image/jpeg")["content_uri"]
            file_name = str(int(self.ts)) + ".jpg"
            self.api.send_content(self.room_id, mxc, file_name, "m.image")
            logger.debug("sent screenshot to " + self.room_id)
        except AttributeError:
            self.api.send_notice(self.room_id, "Error in capturing screenshot")
            logger.error("could not capture screenshot from display")

    def _save(self):
        if self.ts:
            if self.ts + 100 < time.time():
                with self.keyboard.pressed(Key.shift):
                    self._press_key(Key.f1)
                logger.debug("saved current gamestate to f1")

    def _load(self):
        self._press_key(Key.f1)
        logger.debug("loaded gamestate from f1")

    def room_handler(self, room_alias):
        # Only room created is #matrixplayspokemon
        logger.info("homeserver asked for " + room_alias)
        return room_alias == self.config["room_alias"]

    def user_handler(self, mxid):
        # Only user is as_user.mxid
        logger.info("homeserver asked for " + mxid)
        return mxid == self.config["user_id"]

    def transaction_handler(self, event_stream):
        for event in event_stream:
            if (event.id == self.room_id and
              event.type == "m.room.message" and
              event.content["msgtype"] == "m.text"):
                content = event.content["body"].lower()
                if content == "a":
                    self._press_key("x")
                elif content == "b":
                    self._press_key("z")
                elif content == "l":
                    self._press_key("a")
                elif content == "r":
                    self._press_key("s")
                elif content == "up":
                    self._press_key(Key.up)
                elif content == "down":
                    self._press_key(Key.down)
                elif content == "left":
                    self._press_key(Key.left)
                elif content == "right":
                    self._press_key(Key.right)
                elif content == "start":
                    self._press_key(Key.enter)
                elif content == "select":
                    self._press_key(Key.backspace)

                elif content == "dump" and self.config["debug"]:
                    logger.debug("received dump command")
                    self._dump()
                elif content == "save" and self.config["debug"]:
                    logger.debug("received save command")
                    with self.keyboard.pressed(Key.shift):
                        self._press_key(Key.f1)
                    logger.debug("saved current gamestate to f1")
                elif content == "load" and self.config["debug"]:
                    logger.debug("received load command")
                    self._load()

            logger.debug("handled " + event.type +
                         #" from " + event.mxid +
                         " in " + event.id)
            self.send_screenshot()
            self._save()
        return True

    def _press_key(self, key):
        self.keyboard.press(key)
        # make sure the key is pressed long enought to register with mgba
        time.sleep(0.05)
        self.keyboard.release(key)
        logger.debug("pressed key: " + str(key))

    def _dump(self):
        self.pkmn.stop()
        self.warning("mgba stdout: " + self.pkmn.stdout)
        self.warning("mgba stderr: " + self.pkmn.stderr)
        self._start_mgba()

mpp = MPPServer(application, config)
logger.info("setup complete")
application.add_handlers(room_handler=mpp.room_handler,
                         transaction_handler=mpp.transaction_handler,
                         user_handler=mpp.user_handler,)
