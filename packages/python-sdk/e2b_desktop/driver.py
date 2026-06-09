from typing import Iterator, Literal, Optional, Protocol, Tuple, Union

Platform = Literal["linux", "windows"]


class DesktopStream(Protocol):
    def start(
        self,
        vnc_port: Optional[int] = None,
        port: Optional[int] = None,
        require_auth: bool = False,
        window_id: Optional[str] = None,
    ) -> None: ...

    def stop(self) -> None: ...

    def get_url(
        self,
        auto_connect: bool = True,
        view_only: bool = False,
        resize: str = "scale",
        auth_key: Optional[str] = None,
    ) -> str: ...

    def get_auth_key(self) -> str: ...


class DesktopDriver(Protocol):
    @property
    def stream(self) -> DesktopStream: ...

    def start(self) -> None: ...

    def screenshot(
        self, format: Literal["bytes", "stream"] = "bytes"
    ) -> Union[bytearray, Iterator[bytes]]: ...

    def left_click(self, x: Optional[int] = None, y: Optional[int] = None): ...

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None): ...

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None): ...

    def middle_click(self, x: Optional[int] = None, y: Optional[int] = None): ...

    def scroll(self, direction: Literal["up", "down"] = "down", amount: int = 1): ...

    def move_mouse(self, x: int, y: int): ...

    def mouse_press(self, button: Literal["left", "right", "middle"] = "left"): ...

    def mouse_release(self, button: Literal["left", "right", "middle"] = "left"): ...

    def get_cursor_position(self) -> tuple[int, int]: ...

    def get_screen_size(self) -> tuple[int, int]: ...

    def write(
        self, text: str, *, chunk_size: int = 25, delay_in_ms: int = 75
    ) -> None: ...

    def press(self, key: Union[str, list[str]]): ...

    def drag(self, fr: tuple[int, int], to: tuple[int, int]): ...

    def wait(self, ms: int): ...

    def open(self, file_or_url: str): ...

    def get_current_window_id(self) -> str: ...

    def get_application_windows(self, application: str) -> list[str]: ...

    def get_window_title(self, window_id: str) -> str: ...

    def launch(self, application: str, uri: Optional[str] = None): ...


def create_desktop_driver(
    platform: Platform,
    sandbox,
    resolution: Optional[Tuple[int, int]] = None,
    dpi: Optional[int] = None,
    display: Optional[str] = None,
    novnc_command: Optional[str] = None,
) -> DesktopDriver:
    if platform == "linux":
        from .linux import LinuxDesktopDriver

        return LinuxDesktopDriver(
            sandbox,
            resolution=resolution,
            dpi=dpi,
            display=display,
        )
    if platform == "windows":
        from .windows import DEFAULT_WINDOWS_NOVNC_COMMAND, WindowsDesktopDriver

        return WindowsDesktopDriver(
            sandbox,
            novnc_command=novnc_command or DEFAULT_WINDOWS_NOVNC_COMMAND,
        )
    raise ValueError(f"Unsupported desktop platform: {platform}")
