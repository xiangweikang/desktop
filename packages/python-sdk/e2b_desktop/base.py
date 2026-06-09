import time
from typing import Callable, Iterator, Literal, Optional, Union

from e2b import CommandExitException, CommandResult


MouseButton = Literal["left", "right", "middle"]


def chunk_text(text: str, chunk_size: int) -> Iterator[str]:
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


class BaseVNCServer:
    _url: str

    def get_url(
        self,
        auto_connect: bool = True,
        view_only: bool = False,
        resize: str = "scale",
        auth_key: Optional[str] = None,
    ) -> str:
        params = []
        if auto_connect:
            params.append("autoconnect=true")
        if view_only:
            params.append("view_only=true")
        if resize:
            params.append(f"resize={resize}")
        if auth_key:
            params.append(f"password={auth_key}")
        if params:
            return f"{self._url}?{'&'.join(params)}"
        return self._url


class BaseDesktopDriver:
    sandbox: object

    def _run_wait_command(self, cmd: str) -> CommandResult:
        raise NotImplementedError

    def _sleep_between_waits(self, interval: float) -> None:
        time.sleep(interval)

    def _wait_and_verify(
        self,
        cmd: str,
        on_result: Callable[[CommandResult], bool],
        timeout: int = 10,
        interval: float = 0.5,
    ) -> bool:
        elapsed = 0.0
        while elapsed < timeout:
            try:
                if on_result(self._run_wait_command(cmd)):
                    return True
            except CommandExitException:
                pass

            self._sleep_between_waits(interval)
            elapsed += interval

        return False

    def _read_and_remove_file(
        self,
        path: str,
        format: Literal["bytes", "stream"] = "bytes",
    ) -> Union[bytearray, Iterator[bytes]]:
        file = self.sandbox.files.read(  # type: ignore[attr-defined]
            path,
            format=format,
        )
        self.sandbox.files.remove(path)  # type: ignore[attr-defined]
        return file

    def _move_if_coordinates(self, x: Optional[int], y: Optional[int]) -> None:
        if (x is None) != (y is None):
            raise ValueError("Both x and y must be provided together")
        if x is not None and y is not None:
            self.move_mouse(x, y)

    def _click(self, button: MouseButton = "left") -> None:
        raise NotImplementedError

    def _click_at(
        self,
        button: MouseButton = "left",
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> None:
        self._move_if_coordinates(x, y)
        self._click(button)

    def left_click(self, x: Optional[int] = None, y: Optional[int] = None):
        self._click_at("left", x, y)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None):
        self._click_at("right", x, y)

    def middle_click(self, x: Optional[int] = None, y: Optional[int] = None):
        self._click_at("middle", x, y)

    def drag(self, fr: tuple[int, int], to: tuple[int, int]):
        self.move_mouse(fr[0], fr[1])
        self.mouse_press()
        self.move_mouse(to[0], to[1])
        self.mouse_release()

    def move_mouse(self, x: int, y: int):
        raise NotImplementedError

    def mouse_press(self, button: MouseButton = "left"):
        raise NotImplementedError

    def mouse_release(self, button: MouseButton = "left"):
        raise NotImplementedError
