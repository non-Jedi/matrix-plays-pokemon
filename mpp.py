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

from gyr import server, matrix_objects, exceptions
from pyvirtualdisplay.smartdisplay import SmartDisplay
from easyprocess import EasyProcess
import time
import json
from io import BytesIO

# Must start display before we can use Xlib via pynput
disp = SmartDisplay(visible=False, size=(240, 160))
disp.start()
from pynput.keyboard import Key, Controller
# Have to start pulse here because computer is being a weenie
pulse = EasyProcess("pulseaudio")
pulse.start()

with open("config.json") as f:
    config = json.load(f)

application = server.Application(config["hs_address"], config["token"])

class MPPServer:

    def __init__(self, application, config):
        self.config = config
        self.config["room_alias"] = ("#" + self.config["local_room_alias"] +
                                     ":" + self.config["hs_name"])
        self.config["user_id"] = ("@" + self.config["local_user_id"] +
                                  ":" + self.config["hs_name"])

        self.disp = disp
        self.pkmn = EasyProcess("mgba -b " + self.config["bios_location"] + " " + self.config["rom_location"])
        self.pkmn.start()
        self.keyboard = Controller()

        self.api = application.Api()
        try:
            # when creating a room with a room alias, only local part of alias is used
            self.room_id = self.api.create_room(alias=self.config["local_room_alias"],
                                                is_public=True)
        except exceptions.MatrixError:
            # if it already exists just get the room_id
            self.room_id = self.api.get_room_id(self.config["room_alias"])

        self.ts = False
        time.sleep(5)
        self.send_screenshot()

    def __del__(self):
        self.pkmn.stop()
        self.disp.stop()

    def send_screenshot(self):
        if self.ts:
            if self.ts + 2 < time.time():
                self._send()
                self.ts = time.time()
        else:
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
        except AttributeError:
            self.api.send_notice(self.room_id, "Error in capturing screenshot")

    def room_handler(self, room_alias):
        # Only room created is #matrixplayspokemon
        return room_alias == self.config["room_alias"]

    def user_handler(self, mxid):
        # Only user is as_user.mxid
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
            self.send_screenshot()
        return True

    def _press_key(key):
        self.keyboard.press(key)
        # make sure the key is pressed long enought to register with mgba
        time.sleep(0.05)
        self.keyboard.release(key)

mpp = MPPServer(application, config)
application.add_handlers(room_handler=mpp.room_handler,
                         transaction_handler=mpp.transaction_handler,
                         user_handler=mpp.user_handler,)
