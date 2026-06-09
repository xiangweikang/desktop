from typing import Dict, Iterator, Literal, Optional, Tuple, Union, overload

from e2b import Sandbox as SandboxBase
from e2b.connection_config import ApiParams
from typing_extensions import Self, Unpack

from .driver import DesktopDriver, DesktopStream, Platform, create_desktop_driver


class Sandbox(SandboxBase):
    default_template = "desktop"
    _driver: DesktopDriver

    @classmethod
    def create(
        cls,
        template: Optional[str] = None,
        resolution: Optional[Tuple[int, int]] = None,
        dpi: Optional[int] = None,
        display: Optional[str] = None,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
        envs: Optional[Dict[str, str]] = None,
        secure: bool = True,
        allow_internet_access: bool = True,
        platform: Platform = "linux",
        novnc_command: Optional[str] = None,
        **opts: Unpack[ApiParams],
    ) -> Self:
        """
        Create a new desktop sandbox.

        By default, the sandbox is created from the default `desktop` sandbox template.
        """
        display = display or ":0"
        sandbox_envs = dict(envs or {})
        if platform == "linux":
            sandbox_envs["DISPLAY"] = display
        create_envs = sandbox_envs if sandbox_envs else None

        sbx = super().create(
            template=template,
            timeout=timeout,
            metadata=metadata,
            envs=create_envs,
            secure=secure,
            allow_internet_access=allow_internet_access,
            **opts,
        )

        sbx._driver = create_desktop_driver(
            platform,
            sbx,
            resolution=resolution,
            dpi=dpi,
            display=display,
            novnc_command=novnc_command,
        )
        sbx._display = display
        sbx._driver.start()
        return sbx

    @classmethod
    def _cls_connect_sandbox(
        cls,
        sandbox_id: str,
        timeout: Optional[int] = None,
        resolution: Optional[Tuple[int, int]] = None,
        dpi: Optional[int] = None,
        display: Optional[str] = None,
        platform: Platform = "linux",
        novnc_command: Optional[str] = None,
        **opts: Unpack[ApiParams],
    ) -> Self:
        sbx = super()._cls_connect_sandbox(
            sandbox_id=sandbox_id,
            timeout=timeout,
            **opts,
        )
        display = display or ":0"
        sbx._driver = create_desktop_driver(
            platform,
            sbx,
            resolution=resolution,
            dpi=dpi,
            display=display,
            novnc_command=novnc_command,
        )
        sbx._display = display
        if platform == "windows":
            sbx._driver.start()
        return sbx

    @property
    def stream(self) -> DesktopStream:
        return self._driver.stream

    @overload
    def screenshot(self, format: Literal["stream"]) -> Iterator[bytes]:
        """
        Take a screenshot and return it as a stream of bytes.
        """

    @overload
    def screenshot(
        self,
        format: Literal["bytes"],
    ) -> bytearray:
        """
        Take a screenshot and return it as a bytearray.
        """

    def screenshot(
        self,
        format: Literal["bytes", "stream"] = "bytes",
    ):
        return self._driver.screenshot(format=format)

    def left_click(self, x: Optional[int] = None, y: Optional[int] = None):
        return self._driver.left_click(x, y)

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None):
        return self._driver.double_click(x, y)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None):
        return self._driver.right_click(x, y)

    def middle_click(self, x: Optional[int] = None, y: Optional[int] = None):
        return self._driver.middle_click(x, y)

    def scroll(self, direction: Literal["up", "down"] = "down", amount: int = 1):
        return self._driver.scroll(direction, amount)

    def move_mouse(self, x: int, y: int):
        return self._driver.move_mouse(x, y)

    def mouse_press(self, button: Literal["left", "right", "middle"] = "left"):
        return self._driver.mouse_press(button)

    def mouse_release(self, button: Literal["left", "right", "middle"] = "left"):
        return self._driver.mouse_release(button)

    def get_cursor_position(self) -> tuple[int, int]:
        return self._driver.get_cursor_position()

    def get_screen_size(self) -> tuple[int, int]:
        return self._driver.get_screen_size()

    def write(self, text: str, *, chunk_size: int = 25, delay_in_ms: int = 75) -> None:
        return self._driver.write(
            text, chunk_size=chunk_size, delay_in_ms=delay_in_ms
        )

    def press(self, key: Union[str, list[str]]):
        return self._driver.press(key)

    def drag(self, fr: tuple[int, int], to: tuple[int, int]):
        return self._driver.drag(fr, to)

    def wait(self, ms: int):
        return self._driver.wait(ms)

    def open(self, file_or_url: str):
        return self._driver.open(file_or_url)

    def get_current_window_id(self) -> str:
        return self._driver.get_current_window_id()

    def get_application_windows(self, application: str) -> list[str]:
        return self._driver.get_application_windows(application)

    def get_window_title(self, window_id: str) -> str:
        return self._driver.get_window_title(window_id)

    def launch(self, application: str, uri: Optional[str] = None):
        return self._driver.launch(application, uri)
