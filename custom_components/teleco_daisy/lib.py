import asyncio
from typing import Any, ClassVar, Literal

import aiohttp
from pydantic import BaseModel, ConfigDict

base_url = "https://tmate.telecoautomation.com/"


class DaisyStatus(BaseModel):
    """for /status-device-list"""

    idInstallationDeviceStatusitem: int
    idDevicetypeStatusitemModel: int
    statusitemCode: str
    statusItem: str
    statusValue: str
    lowlevelStatusitem: None | str = None


class DaisyInstallation(BaseModel):
    activetimer: str
    firmwareVersion: str
    idInstallation: int
    idInstallationDevice: int
    instCode: str
    instDescription: str
    installationOrder: int
    latitude: float | None
    longitude: float | None
    weekend: str | None  # list[str]
    workdays: str | None  # list[str]

    def __str__(self):
        return f"DaisyInstallation fw{self.firmwareVersion}"


class DaisyBaseDevice(BaseModel):
    activetimer: str
    deviceCode: str
    deviceIndex: int
    deviceOrder: int
    directOnly: str | None = None
    favorite: str
    feedback: str
    idDevicemodel: int
    idDevicetype: int
    idInstallationDevice: int
    label: str
    remoteControlCode: str


class DaisyDevice(DaisyBaseDevice):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    client: "TelecoDaisy"
    installation: DaisyInstallation

    def __str__(self):
        return f'{self.__class__.__name__} "{self.label}"'

    async def command(self, params: dict, ignore_ack: bool = False):
        return await self.client.feed_the_commands(
            installation=self.installation,
            commandsList=[
                {
                    "deviceCode": str(self.deviceIndex),
                    "idInstallationDevice": self.idInstallationDevice,
                }
                | params
            ],
            ignore_ack=ignore_ack,
        )

    async def update_state(self) -> list[DaisyStatus]:
        return await self.client.status_device_list(self.installation, self)


class DaisyDeviceWithCommands(DaisyBaseDevice):
    class DeviceCommand(BaseModel):
        commandAction: str
        commandCode: str
        commandParam: str
        deviceIndex: int
        idDevicetypeCommandModel: int
        idInstallationDeviceCommand: int
        lowlevelCommand: str

    deviceCommandList: list[DeviceCommand]

    def __str__(self):
        return (
            f'DaisyDevice "{self.label}" '
            f"(deviceType: {self.idDevicetype}, deviceModel: {self.idDevicemodel})"
        )


class DaisyRoom(BaseModel):
    idInstallationRoom: int
    idRoomtype: int
    roomDescription: str
    roomOrder: int
    deviceList: list[DaisyDevice]

    def __str__(self):
        return f'DaisyRoom "{self.roomDescription}"'


class DaisyRoomWithCommands(DaisyRoom):
    deviceList: list[DaisyDeviceWithCommands]


class DaisyCover(DaisyDevice):
    is_closed: bool | None = None

    osc_map: dict[Literal["open", "stop", "close"], dict[str, Any]]

    async def update_state(self):
        stati = await super().update_state()
        for status in stati:
            if status.statusitemCode == "OPEN_CLOSE":
                match status.statusValue:
                    case "CLOSE":
                        self.is_closed = True
                    case "OPEN":
                        self.is_closed = False
                    case _:
                        self.is_closed = None
        return stati

    async def open_cover(self):
        return await self._open_stop_close("open")

    async def stop_cover(self):
        await self._open_stop_close("stop")

    async def close_cover(self):
        await self._open_stop_close("close")

    async def _open_stop_close(self, open_stop_close: Literal["open", "stop", "close"]):
        return await self.command(
            {"commandAction": "OPEN_STOP_CLOSE"} | self.osc_map[open_stop_close]
        )


class DaisySlatsCover(DaisyCover):
    position: int | None = None

    osc_map: dict[Literal["open", "stop", "close"], dict[str, Any]] = {
        "open": {"commandId": 94, "commandParam": "OPEN", "lowlevelCommand": "CH4"},
        "stop": {"commandId": 95, "commandParam": "STOP", "lowlevelCommand": "CH7"},
        "close": {"commandId": 96, "commandParam": "CLOSE", "lowlevelCommand": "CH1"},
    }

    async def open_cover(self, percent: Literal["33", "66", "100"] | None = None):
        if percent == "100" or percent is None:
            return await self._open_stop_close("open")

        percent_map = {
            "33": {"commandParam": "LEV2", "commandId": 97, "lowlevelCommand": "CH2"},
            "66": {"commandParam": "LEV3", "commandId": 98, "lowlevelCommand": "CH3"},
            "100": {"commandParam": "LEV4", "commandId": 99, "lowlevelCommand": "CH4"},
        }

        return await self.command({"commandAction": "LEVEL"} | percent_map[percent])

    async def update_state(self):
        stati = await super().update_state()
        for status in stati:
            if status.statusitemCode == "LEVEL":
                self.position = int(status.statusValue)
        return stati


class DaisyRetractableSlatsCover(DaisyCover):
    position: int | None = None

    osc_map: dict[Literal["open", "stop", "close"], dict[str, Any]] = {
        "open": {"commandId": 206, "commandParam": "OPEN", "lowlevelCommand": "CH5"},
        "stop": {"commandId": 207, "commandParam": "STOP", "lowlevelCommand": "CH7"},
        "close": {"commandId": 208, "commandParam": "CLOSE", "lowlevelCommand": "CH8"},
    }

    async def open_cover_tilt(
        self, percent: Literal["0", "33", "66", "100"] | None = None
    ):
        percent_map = {
            "0": {"commandParam": "LEV1", "commandId": 214, "lowlevelCommand": "CH1"},
            "33": {"commandParam": "LEV2", "commandId": 210, "lowlevelCommand": "CH2"},
            "66": {"commandParam": "LEV3", "commandId": 211, "lowlevelCommand": "CH3"},
            "100": {"commandParam": "LEV4", "commandId": 212, "lowlevelCommand": "CH4"},
        }

        return await self.command({"commandAction": "LEVEL"} | percent_map[percent])

    async def update_state(self):
        stati = await super().update_state()
        for status in stati:
            if status.statusitemCode == "LEVEL":
                self.position = int(status.statusValue)
        return stati


class DaisyShadeCover(DaisyCover):
    pass


class DaisyAwningCover(DaisyCover):
    pass


class DaisyLight(DaisyDevice):
    is_on: bool | None = None
    brightness: int | None = None  # from 0 to 100

    async def update_state(self):
        stati = await super().update_state()
        for status in stati:
            if status.statusitemCode == "POWER":
                self.is_on = status.statusValue == "ON"
        return stati

    async def set_brightness(self, brightness: int):
        raise NotImplementedError

    async def _turn_on(self, specific_params: dict):
        return await self.command(
            {"commandAction": "POWER", "commandParam": "ON"} | specific_params
        )

    async def _turn_off(self, specific_params: dict):
        return await self.command(
            {"commandAction": "POWER", "commandParam": "OFF"} | specific_params
        )


class DaisyRGBLight(DaisyLight):
    rgb: tuple[int, int, int] | None = None

    async def update_state(self):
        stati = await super().update_state()
        for status in stati:
            if status.statusitemCode == "COLOR":
                val = status.statusValue
                self.brightness = int(val[1:4])
                self.rgb = (int(val[5:8]), int(val[9:12]), int(val[13:16]))
        return stati

    async def set_rgb_and_brightness(
        self, rgb: tuple[int, int, int] | None = None, brightness: int | None = None
    ):
        if brightness is None:
            brightness = self.brightness or 0
        if 0 > brightness or brightness > 100:
            raise ValueError("Brightness must be between 0 and 100")
        if rgb is None:
            rgb = self.rgb or (255, 255, 255)
        if any((c < 0 or c > 255) for c in rgb):
            raise ValueError("Color must be between 0 and 255")

        v = f"A{brightness:03d}R{rgb[0]:03d}G{rgb[1]:03d}B{rgb[2]:03d}"

        return await self.command(
            {
                "commandAction": "COLOR",
                "commandId": 137,
                "commandParam": v,
                "lowlevelCommand": None,
            }
        )

    async def turn_on(self):
        return await self._turn_on({"commandId": 138, "lowlevelCommand": None})

    async def turn_off(self):
        return await self._turn_off({"commandId": 138, "lowlevelCommand": None})


# class DaisyWhiteLight(DaisyLight):
#     def set_brightness(self, brightness: int):
#         if brightness is None:
#             brightness = self.brightness or 0
#         if 0 > brightness or brightness > 100:
#             raise ValueError("Brightness must be between 0 and 100")
#
#         v = f"A{brightness:03d}R255G255B255"
#
#         return self.command(
#             {
#                 "commandAction": "COLOR",
#                 "commandId": 146,
#                 "commandParam": v,
#                 "lowlevelCommand": "CH1",
#             }
#         )
#
#     def turn_on(self):
#         # https://github.com/andreasnuesslein/py-teleco-daisy/issues/10
#         if self.idDevicetype == 21 and self.idDevicemodel == 17:
#             return self._turn_on({"commandId": 40, "lowlevelCommand": "CH1"})
#         return self._turn_on({"commandId": 146, "lowlevelCommand": "CH1"})
#
#     def turn_off(self):
#         # https://github.com/andreasnuesslein/py-teleco-daisy/issues/10
#         if self.idDevicetype == 21 and self.idDevicemodel == 17:
#             return self._turn_off({"commandId": 41, "lowlevelCommand": "CH8"})
#         return self._turn_off({"commandId": 147, "lowlevelCommand": "CH8"})


class DaisyWhite4LevelLight(DaisyLight):
    brightness_map: dict[Literal[25, 50, 75, 100], dict[str, Any]]

    async def set_brightness(self, brightness: int):
        if brightness is None:
            brightness = self.brightness or 0
        if 0 > brightness or brightness > 100:
            raise ValueError("Brightness must be between 0 and 100")

        if brightness is None or brightness == 0:
            return await self.turn_off()

        if 1 <= brightness <= 37:
            vals = self.brightness_map[25]
        elif 38 <= brightness <= 62:
            vals = self.brightness_map[50]
        elif 63 <= brightness <= 87:
            vals = self.brightness_map[75]
        else:  # 76-100
            vals = self.brightness_map[100]

        return await self.command({"commandAction": "LEVEL"} | vals)

    async def turn_on(self):
        if self.idDevicetype == 21 and self.idDevicemodel == 17:
            return await self._turn_on({"commandId": 40, "lowlevelCommand": "CH1"})
        if self.idDevicetype == 21 and self.idDevicemodel == 34:
            return await self._turn_on({"commandId": 146, "lowlevelCommand": "CH1"})

        # legacy, without devicemodelmatching
        return await self._turn_on({"commandId": 146, "lowlevelCommand": "CH1"})

    async def turn_off(self):
        # https://github.com/andreasnuesslein/py-teleco-daisy/issues/10
        if self.idDevicetype == 21 and self.idDevicemodel == 17:
            return await self._turn_off({"commandId": 41, "lowlevelCommand": "CH8"})
        if self.idDevicetype == 21 and self.idDevicemodel == 34:
            return await self._turn_on({"commandId": 147, "lowlevelCommand": "CH8"})

        # legacy, without devicemodelmatching
        return await self._turn_off({"commandId": 147, "lowlevelCommand": "CH8"})

    async def update_state(self):
        stati = await super().update_state()
        for status in stati:
            if status.statusitemCode == "POWER":
                self.is_on = status.statusValue == "ON"
            elif status.statusitemCode == "LEVEL":
                try:
                    self.brightness = {
                        "25": 25,
                        "50": 50,
                        "75": 75,
                        "100": 100,
                    }[status.statusValue]
                except KeyError:
                    self.brightness = 50
        return stati


class DaisyChannelLight(DaisyLight):
    """A single channel of Teleco's generic virtual remote (GEN_BUTT).

    Devicetype 27 / devicemodel 41 is a generic multi-channel remote whose
    buttons get memorised into a receiver. A receiver typically learns one
    button as a toggle (press = on, press again = off) and reports no
    feedback ("feedback": "N"), so state is assumed: on and off both fire
    the same channel command and the ack is ignored (a feedback-less
    device never reaches the "PROC" ack state).

    Some receivers (e.g. the WiseBox 4) can instead memorise a channel
    PAIR as dedicated on/off buttons. If the receiver was programmed that
    way, set off_channel to the second channel of the pair and turn_off
    fires it instead of re-firing the toggle.
    """

    # idDevicetypeCommandModel per channel, constant for devicetype 27 / model 41
    channel_command_ids: ClassVar[dict[str, int]] = {
        "CH1": 170,
        "CH2": 171,
        "CH3": 172,
        "CH4": 173,
        "CH5": 174,
        "CH7": 175,
        "CH8": 176,
    }

    channel: str = "CH1"
    off_channel: str | None = None

    async def _press(self, channel: str):
        return await self.command(
            {
                "commandAction": "CHANNEL",
                "commandCode": "GEN_BUTT",
                "commandParam": channel,
                "commandId": self.channel_command_ids[channel],
                "lowlevelCommand": channel,
            },
            ignore_ack=True,
        )

    async def turn_on(self):
        res = await self._press(self.channel)
        self.is_on = True
        return res

    async def turn_off(self):
        res = await self._press(self.off_channel or self.channel)
        self.is_on = False
        return res

    async def update_state(self):
        # no feedback exists for this device; state is assumed
        return []


class DaisyHeater4CH(DaisyDevice):
    async def turn_on(self):
        return await self.command(
            {
                "commandAction": "POWER",
                "commandParam": "ON",
                "lowlevelCommand": "CH1",
                "commandId": 58,
            }
        )

    async def turn_off(self):
        return await self.command(
            {
                "commandAction": "POWER",
                "commandParam": "OFF",
                "lowlevelCommand": "CH4",
                "commandId": 59,
            }
        )

    async def set_level(self, level: Literal["50", "75", "100"]):
        if level == "50":
            cmd = {
                # "idDevicetypeCommandModel": 60,
                "commandId": 60,
                "commandParam": "LEV2",
                "lowlevelCommand": "CH3",
            }
        elif level == "75":
            cmd = {
                # "idDevicetypeCommandModel": 61,
                "commandId": 61,
                "commandParam": "LEV3",
                "lowlevelCommand": "CH2",
            }
        else:
            cmd = {
                # "idDevicetypeCommandModel": 62,
                "commandId": 62,
                "commandParam": "LEV4",
                "lowlevelCommand": "CH1",
            }

        return await self.command({"commandAction": "LEVEL"} | cmd)


# device classes that need no extra constructor data, by (idDevicetype, idDevicemodel)
SIMPLE_DEVICE_CLASSES = {
    (21, 20): DaisyHeater4CH,
    (23, 32): DaisyRGBLight,
    (24, 27): DaisySlatsCover,
    (24, 44): DaisyRetractableSlatsCover,
    (27, 41): DaisyChannelLight,
}


def create_specific_device(dev):
    if cls := SIMPLE_DEVICE_CLASSES.get((dev["idDevicetype"], dev["idDevicemodel"])):
        return cls(**dev)

    match dev:
        case {"idDevicetype": 21, "idDevicemodel": 17}:
            dev["brightness_map"] = {
                25: {"commandParam": "LEV1", "commandId": 42, "lowlevelCommand": "CH4"},
                50: {"commandParam": "LEV2", "commandId": 43, "lowlevelCommand": "CH3"},
                75: {"commandParam": "LEV3", "commandId": 44, "lowlevelCommand": "CH2"},
                100: {
                    "commandParam": "LEV4",
                    "commandId": 45,
                    "lowlevelCommand": "CH1",
                },
            }
            return DaisyWhite4LevelLight(**dev)

        case {"idDevicetype": 21, "idDevicemodel": 34}:
            dev["brightness_map"] = {
                25: {
                    "commandParam": "LEV1",
                    "commandId": 141,
                    "lowlevelCommand": "CH4",
                },
                50: {
                    "commandParam": "LEV2",
                    "commandId": 142,
                    "lowlevelCommand": "CH3",
                },
                75: {
                    "commandParam": "LEV3",
                    "commandId": 143,
                    "lowlevelCommand": "CH2",
                },
                100: {
                    "commandParam": "LEV4",
                    "commandId": 144,
                    "lowlevelCommand": "CH1",
                },
            }
            return DaisyWhite4LevelLight(**dev)

        case {"idDevicetype": 22, "idDevicemodel": 21}:
            dev["osc_map"] = {
                "open": {
                    "commandId": 63,
                    "commandParam": "OPEN",
                    "lowlevelCommand": "CH5",
                },
                "stop": {
                    "commandId": 64,
                    "commandParam": "STOP",
                    "lowlevelCommand": "CH7",
                },
                "close": {
                    "commandId": 65,
                    "commandParam": "CLOSE",
                    "lowlevelCommand": "CH8",
                },
            }
            return DaisyAwningCover(**dev)

        case {"idDevicetype": 22, "idDevicemodel": 25}:
            dev["osc_map"] = {
                "open": {
                    "commandId": 75,
                    "commandParam": "OPEN",
                    "lowlevelCommand": "CH5",
                },
                "stop": {
                    "commandId": 76,
                    "commandParam": "STOP",
                    "lowlevelCommand": "CH7",
                },
                "close": {
                    "commandId": 77,
                    "commandParam": "CLOSE",
                    "lowlevelCommand": "CH8",
                },
            }
            return DaisyShadeCover(**dev)

        case {"idDevicetype": 22, "idDevicemodel": 31}:
            dev["osc_map"] = {
                "open": {
                    "commandId": 111,
                    "commandParam": "OPEN",
                    "lowlevelCommand": "CH5",
                },
                "stop": {
                    "commandId": 112,
                    "commandParam": "STOP",
                    "lowlevelCommand": "CH7",
                },
                "close": {
                    "commandId": 113,
                    "commandParam": "CLOSE",
                    "lowlevelCommand": "CH8",
                },
            }
            return DaisyShadeCover(**dev)

        case _:
            return DaisyDevice(**dev)


class TelecoDaisy:
    idAccount: int | None = None
    idSession: str | None = None

    def __init__(self, email, password, session: aiohttp.ClientSession | None = None):
        self.email = email
        self.password = password
        self._session = session
        self._close_session = False

        self._auth = aiohttp.BasicAuth("teleco", "tmate20")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._close_session = True
        return self._session

    async def close(self):
        """Clean up the session if we created it."""
        if self._session and self._close_session:
            await self._session.close()

    async def _tmate20_post(self, url, json: dict | None = None) -> dict:
        payload = {"idSession": self.idSession}
        if json:
            payload |= json

        session = await self._get_session()
        async with session.post(base_url + url, json=payload, auth=self._auth) as req:
            req.raise_for_status()  # Good practice to raise on 400/500 errors
            return await req.json()

    async def _post(self, url, json: dict | None = None, unauth=False) -> dict:
        if unauth:
            _json = json
        else:
            _json = {"idSession": self.idSession, "idAccount": self.idAccount}
            if json:
                _json |= json

        session = await self._get_session()
        async with session.post(base_url + url, json=_json, auth=self._auth) as req:
            req.raise_for_status()
            req_json = await req.json()

        if req_json["codEsito"] != "S":
            raise Exception(req_json)
        return req_json["valRisultato"]

    async def login(self):
        login = await self._post(
            "teleco/services/account-login",
            {"email": self.email, "pwd": self.password},
            unauth=True,
        )
        self.idAccount = login["idAccount"]
        self.idSession = login["idSession"]

    async def get_account_installation_list(self) -> list[DaisyInstallation]:
        req = await self._post("teleco/services/account-installation-list")
        return [DaisyInstallation(**inst) for inst in req["installationList"]]

    async def get_installation_is_active(self, installation: DaisyInstallation):
        res = await self._tmate20_post(
            "teleco/services/tmate20/nodestatus/",
            {"idInstallation": installation.instCode},
        )
        return res["nodeActive"]

    async def get_room_configuration_list(self, installation: DaisyInstallation):
        req = await self._post(
            "teleco/services/room-configuration-list",
            {"idInstallation": installation.idInstallation},
        )
        return [DaisyRoomWithCommands(**dr) for dr in req["roomList"]]

    async def get_room_list(self, installation: DaisyInstallation) -> list[DaisyRoom]:
        room_list = await self._post(
            "teleco/services/room-list",
            {"idInstallation": installation.idInstallation},
        )

        rooms = []
        for room in room_list["roomList"]:
            device_list = []
            for dv in room["deviceList"]:
                dv["installation"] = installation
                dv["client"] = self
                device_list += [create_specific_device(dv)]
            rooms += [DaisyRoom(**room | {"deviceList": device_list})]

        return rooms

    async def status_device_list(
        self, installation: DaisyInstallation, device: DaisyDevice
    ) -> list[DaisyStatus]:
        status_device_list = await self._post(
            "teleco/services/status-device-list",
            {
                "idInstallation": installation.idInstallation,
                "idInstallationDevice": device.idInstallationDevice,
            },
        )

        return [DaisyStatus(**x) for x in status_device_list["statusitemList"]]

    async def _scenario_list(self, installation: DaisyInstallation):
        req = await self._post(
            "teleco/services/scenario-list",
            {
                "idInstallation": installation.idInstallation,
            },
        )
        return req

    async def _command_scenario_list(
        self, installation: DaisyInstallation, szenario_id
    ):
        req = await self._post(
            "teleco/services/command-scenario-list",
            json={
                "idInstallation": installation.idInstallation,
                "idInstallationScenario": szenario_id,
            },
        )
        return req

    async def feed_the_commands(
        self,
        installation: DaisyInstallation,
        commandsList: list[dict],
        ignore_ack=False,
    ):
        res = await self._tmate20_post(
            "teleco/services/tmate20/feedthecommands/",
            json={
                "commandsList": commandsList,
                "idInstallation": installation.instCode,
                "idScenario": 0,
                "isScenario": False,
            },
        )
        if res["MessageID"] != "WS-000":
            raise Exception(res)

        if ignore_ack:
            return {"success": None}

        return await self._get_ack(installation, res["ActionReference"])

    async def _get_ack(self, installation: DaisyInstallation, action_reference: str):
        res = await self._tmate20_post(
            "teleco/services/tmate20/getackcommand/",
            json={
                "id": action_reference,
                "idInstallation": installation.instCode,
                "idSession": self.idSession,
            },
        )
        if res["MessageID"] != "WS-300":
            raise AssertionError()
        if res["MessageText"] == "RCV":
            await asyncio.sleep(0.5)
            return await self._get_ack(installation, action_reference)
        if res["MessageText"] == "PROC":
            return {"success": True}
        return {"success": False}
