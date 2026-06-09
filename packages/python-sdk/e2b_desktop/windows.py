import json
from typing import Iterator, Literal, Optional, Union
from uuid import uuid4

from e2b import CommandExitException, CommandHandle, TimeoutException

from .base import BaseDesktopDriver, BaseVNCServer, MouseButton, chunk_text
from .powershell import ps_single_quote

DEFAULT_WINDOWS_NOVNC_COMMAND = (
    "python C:\\noVNC\\utils\\novnc_proxy "
    "--vnc 127.0.0.1:{vnc_port} "
    "--listen {port} "
    "--web C:\\noVNC"
)

MOUSE_BUTTONS = {
    "left": ("0x0002", "0x0004"),
    "right": ("0x0008", "0x0010"),
    "middle": ("0x0020", "0x0040"),
}

WINDOWS_KEYS = {
    "backspace": "{BACKSPACE}",
    "del": "{DELETE}",
    "delete": "{DELETE}",
    "down": "{DOWN}",
    "end": "{END}",
    "enter": "{ENTER}",
    "esc": "{ESC}",
    "escape": "{ESC}",
    "f1": "{F1}",
    "f2": "{F2}",
    "f3": "{F3}",
    "f4": "{F4}",
    "f5": "{F5}",
    "f6": "{F6}",
    "f7": "{F7}",
    "f8": "{F8}",
    "f9": "{F9}",
    "f10": "{F10}",
    "f11": "{F11}",
    "f12": "{F12}",
    "home": "{HOME}",
    "insert": "{INSERT}",
    "left": "{LEFT}",
    "page_down": "{PGDN}",
    "page_up": "{PGUP}",
    "right": "{RIGHT}",
    "space": " ",
    "tab": "{TAB}",
    "up": "{UP}",
    "win": "^{ESC}",
    "windows": "^{ESC}",
}

WINDOWS_MODIFIER_KEYS = {
    "alt": "%",
    "control": "^",
    "ctrl": "^",
    "shift": "+",
}

SENDKEYS_TEXT_ESCAPES = {
    "{": "{{}",
    "}": "{}}",
    "+": "{+}",
    "^": "{^}",
    "%": "{%}",
    "~": "{~}",
    "(": "{(}",
    ")": "{)}",
    "[": "{[}",
    "]": "{]}",
}


def _escape_sendkeys_text(text: str) -> str:
    escaped = []
    for char in text:
        if char == "\n":
            escaped.append("{ENTER}")
        elif char == "\t":
            escaped.append("{TAB}")
        else:
            escaped.append(SENDKEYS_TEXT_ESCAPES.get(char, char))
    return "".join(escaped)


def _map_sendkeys_key(key: str, *, in_combo: bool = False) -> str:
    lower_key = key.lower()
    if in_combo and lower_key in WINDOWS_MODIFIER_KEYS:
        return WINDOWS_MODIFIER_KEYS[lower_key]
    if lower_key in WINDOWS_KEYS:
        return WINDOWS_KEYS[lower_key]
    if len(key) == 1:
        return _escape_sendkeys_text(key)
    raise ValueError(f"Unsupported Windows key: {key}")


class WindowsVNCServer(BaseVNCServer):
    def __init__(
        self,
        driver: "WindowsDesktopDriver",
        novnc_command: str = DEFAULT_WINDOWS_NOVNC_COMMAND,
    ) -> None:
        self.__driver = driver
        self.__desktop = driver.sandbox
        self.__novnc_handle: Optional[CommandHandle] = None
        self._novnc_command = novnc_command
        self._vnc_port = 5900
        self._port = 6080
        self._url = f"https://{self.__desktop.get_host(self._port)}/vnc.html"

    def _wait_for_port(self, port: int) -> bool:
        return self.__driver._wait_and_verify(
            f"""
$connection = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue
if ($null -eq $connection) {{ exit 1 }}
""",
            lambda r: r.exit_code == 0,
        )

    def _check_novnc_running(self) -> bool:
        try:
            self.__driver._run_ps(
                f"""
$connection = Get-NetTCPConnection -LocalPort {self._port} -ErrorAction SilentlyContinue
if ($null -eq $connection) {{ exit 1 }}
"""
            )
            return True
        except CommandExitException:
            return False

    def get_auth_key(self) -> str:
        raise RuntimeError("Stream auth keys are not supported on Windows yet")

    def start(
        self,
        vnc_port: Optional[int] = None,
        port: Optional[int] = None,
        require_auth: bool = False,
        window_id: Optional[str] = None,
    ) -> None:
        if window_id:
            raise NotImplementedError(
                "Window-level operations are not supported on Windows yet"
            )
        self._vnc_port = vnc_port or self._vnc_port
        self._port = port or self._port
        self._url = f"https://{self.__desktop.get_host(self._port)}/vnc.html"

        if require_auth:
            raise NotImplementedError(
                "VNC authentication is not supported on Windows yet"
            )
        if self._check_novnc_running():
            raise RuntimeError("Stream is already running")

        command = self._novnc_command.format(
            vnc_port=self._vnc_port,
            port=self._port,
        )
        self.__novnc_handle = self.__driver._run_ps(command, background=True, timeout=0)
        if not self._wait_for_port(self._port):
            raise TimeoutException("Could not start noVNC server")

    def stop(self) -> None:
        if self.__novnc_handle:
            self.__novnc_handle.kill()
            self.__novnc_handle = None


class WindowsDesktopDriver(BaseDesktopDriver):
    def __init__(
        self,
        sandbox,
        novnc_command: str = DEFAULT_WINDOWS_NOVNC_COMMAND,
    ) -> None:
        self.sandbox = sandbox
        self._stream = WindowsVNCServer(self, novnc_command=novnc_command)

    @property
    def stream(self) -> WindowsVNCServer:
        return self._stream

    def _run_ps(self, script: str, **kwargs):
        return self.sandbox.commands.run(script, shell="powershell", **kwargs)

    def _run_wait_command(self, cmd: str):
        return self._run_ps(cmd)

    def _sleep_between_waits(self, interval: float) -> None:
        self.wait(int(interval * 1000))

    def start(self) -> None:
        self._run_ps("$PSVersionTable.PSVersion.ToString()")

    def _parse_json_stdout(self, stdout: str):
        try:
            return json.loads(stdout.strip())
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse PowerShell JSON output: {stdout}"
            ) from e

    def screenshot(
        self,
        format: Literal["bytes", "stream"] = "bytes",
    ) -> Union[bytearray, Iterator[bytes]]:
        file_name = f"screenshot-{uuid4()}.png"
        result = self._run_ps(
            f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$path = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), {ps_single_quote(file_name)})
$bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
$path
"""
        )
        screenshot_path = result.stdout.strip()
        return self._read_and_remove_file(screenshot_path, format=format)

    def _mouse_event(self, flag: str, data: int = 0) -> None:
        self._run_ps(
            f"""
if (-not ("E2BDesktop.User32" -as [type])) {{
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace E2BDesktop {{
    public class User32 {{
        [DllImport("user32.dll")]
        public static extern void mouse_event(uint dwFlags, uint dx, uint dy, int dwData, UIntPtr dwExtraInfo);
    }}
}}
'@
}}
[E2BDesktop.User32]::mouse_event({flag}, 0, 0, {data}, [UIntPtr]::Zero)
"""
        )

    def _click(self, button: MouseButton = "left") -> None:
        self.mouse_press(button)
        self.mouse_release(button)

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None):
        self._move_if_coordinates(x, y)
        for _ in range(2):
            self.mouse_press("left")
            self.mouse_release("left")
            self.wait(50)

    def scroll(self, direction: Literal["up", "down"] = "down", amount: int = 1):
        delta = 120 * amount if direction == "up" else -120 * amount
        self._mouse_event("0x0800", delta)

    def move_mouse(self, x: int, y: int):
        self._run_ps(
            f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y})
"""
        )

    def mouse_press(self, button: Literal["left", "right", "middle"] = "left"):
        self._mouse_event(MOUSE_BUTTONS[button][0])

    def mouse_release(self, button: Literal["left", "right", "middle"] = "left"):
        self._mouse_event(MOUSE_BUTTONS[button][1])

    def get_cursor_position(self) -> tuple[int, int]:
        result = self._run_ps(
            """
Add-Type -AssemblyName System.Windows.Forms
$position = [System.Windows.Forms.Cursor]::Position
[PSCustomObject]@{ x = $position.X; y = $position.Y } | ConvertTo-Json -Compress
"""
        )
        position = self._parse_json_stdout(result.stdout)
        return int(position["x"]), int(position["y"])

    def get_screen_size(self) -> tuple[int, int]:
        result = self._run_ps(
            """
Add-Type -AssemblyName System.Windows.Forms
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
[PSCustomObject]@{ width = $bounds.Width; height = $bounds.Height } | ConvertTo-Json -Compress
"""
        )
        size = self._parse_json_stdout(result.stdout)
        return int(size["width"]), int(size["height"])

    def write(self, text: str, *, chunk_size: int = 25, delay_in_ms: int = 75) -> None:
        for text_chunk in chunk_text(text, chunk_size):
            chunk = _escape_sendkeys_text(text_chunk)
            self._run_ps(
                f"""
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait({ps_single_quote(chunk)})
Start-Sleep -Milliseconds {delay_in_ms}
"""
            )

    def press(self, key: Union[str, list[str]]):
        if isinstance(key, list):
            mapped_key = "".join(_map_sendkeys_key(k, in_combo=True) for k in key)
        else:
            mapped_key = _map_sendkeys_key(key)

        self._run_ps(
            f"""
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait({ps_single_quote(mapped_key)})
"""
        )

    def wait(self, ms: int):
        self._run_ps(f"Start-Sleep -Milliseconds {ms}")

    def open(self, file_or_url: str):
        self._run_ps(f"Start-Process {ps_single_quote(file_or_url)}")

    def get_current_window_id(self) -> str:
        raise NotImplementedError(
            "Window-level operations are not supported on Windows yet"
        )

    def get_application_windows(self, application: str) -> list[str]:
        raise NotImplementedError(
            "Window-level operations are not supported on Windows yet"
        )

    def get_window_title(self, window_id: str) -> str:
        raise NotImplementedError(
            "Window-level operations are not supported on Windows yet"
        )

    def launch(self, application: str, uri: Optional[str] = None):
        if uri is None:
            self._run_ps(f"Start-Process {ps_single_quote(application)}")
            return

        self._run_ps(
            f"Start-Process {ps_single_quote(application)} {ps_single_quote(uri)}"
        )
