import pytest

from e2b_desktop import main
from e2b_desktop.linux import LinuxDesktopDriver
from e2b_desktop.main import Sandbox
from e2b_desktop.windows import WindowsDesktopDriver


class FakeResult:
    def __init__(self, stdout="", exit_code=0):
        self.stdout = stdout
        self.exit_code = exit_code


class FakeHandle:
    pid = "123"

    def __init__(self):
        self.disconnected = False
        self.killed = False

    def disconnect(self):
        self.disconnected = True

    def kill(self):
        self.killed = True


class FakeCommands:
    def __init__(self):
        self.calls = []

    def run(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if kwargs.get("background"):
            return FakeHandle()
        return FakeResult()


class FakeFiles:
    def read(self, path, format="bytes"):
        return bytearray(b"image")

    def remove(self, path):
        return None


class FakeSandbox:
    def __init__(self):
        self.commands = FakeCommands()
        self.files = FakeFiles()

    def get_host(self, port):
        return f"host-{port}"


def patch_base_create(monkeypatch):
    def fake_create(cls, **kwargs):
        sbx = Sandbox.__new__(Sandbox)
        sbx.created_kwargs = kwargs
        sbx.get_host = lambda port: f"host-{port}"
        return sbx

    monkeypatch.setattr(main.SandboxBase, "create", classmethod(fake_create))


def test_create_platform_linux_selects_linux_driver(monkeypatch):
    patch_base_create(monkeypatch)
    monkeypatch.setattr(LinuxDesktopDriver, "start", lambda self: None)

    sandbox = Sandbox.create(platform="linux", display=":1")

    assert isinstance(sandbox._driver, LinuxDesktopDriver)
    assert sandbox.created_kwargs["envs"]["DISPLAY"] == ":1"


def test_create_platform_windows_selects_windows_driver(monkeypatch):
    patch_base_create(monkeypatch)
    monkeypatch.setattr(WindowsDesktopDriver, "start", lambda self: None)

    sandbox = Sandbox.create(platform="windows", template="windows-desktop")

    assert isinstance(sandbox._driver, WindowsDesktopDriver)
    assert sandbox.created_kwargs["envs"] is None


def test_connect_platform_windows_selects_windows_driver(monkeypatch):
    def fake_connect(cls, sandbox_id, timeout=None, **kwargs):
        sbx = Sandbox.__new__(Sandbox)
        sbx.connected_args = (sandbox_id, timeout, kwargs)
        sbx.get_host = lambda port: f"host-{port}"
        return sbx

    monkeypatch.setattr(
        main.SandboxBase, "_cls_connect_sandbox", classmethod(fake_connect)
    )
    monkeypatch.setattr(WindowsDesktopDriver, "start", lambda self: None)

    sandbox = Sandbox.connect("sandbox-id", platform="windows")

    assert isinstance(sandbox._driver, WindowsDesktopDriver)
    assert sandbox.connected_args[0] == "sandbox-id"


def test_public_methods_delegate_to_driver():
    class Driver:
        stream = object()

        def __init__(self):
            self.calls = []

        def left_click(self, x=None, y=None):
            self.calls.append(("left_click", x, y))
            return "clicked"

    sandbox = Sandbox.__new__(Sandbox)
    sandbox._driver = Driver()

    assert sandbox.left_click(10, 20) == "clicked"
    assert sandbox._driver.calls == [("left_click", 10, 20)]


def test_windows_driver_uses_powershell_for_commands():
    sandbox = FakeSandbox()
    driver = WindowsDesktopDriver(sandbox)

    driver.wait(250)
    driver.open("https://example.com")
    driver.launch("notepad.exe", "C:\\tmp\\note.txt")

    assert sandbox.commands.calls
    assert all(kwargs["shell"] == "powershell" for _, kwargs in sandbox.commands.calls)


def test_windows_window_level_operations_are_not_implemented():
    driver = WindowsDesktopDriver(FakeSandbox())

    with pytest.raises(NotImplementedError):
        driver.get_current_window_id()
    with pytest.raises(NotImplementedError):
        driver.get_application_windows("chrome")
    with pytest.raises(NotImplementedError):
        driver.get_window_title("1")
    with pytest.raises(NotImplementedError):
        driver.stream.start(window_id="1")


def test_linux_driver_command_strings_match_existing_behavior():
    sandbox = FakeSandbox()
    driver = LinuxDesktopDriver(sandbox, display=":7")

    driver.move_mouse(10, 20)
    driver.press(["ctrl", "c"])
    driver.wait(500)

    assert sandbox.commands.calls[0][0] == "xdotool mousemove --sync 10 20"
    assert sandbox.commands.calls[1][0] == "xdotool key Control_L+c"
    assert sandbox.commands.calls[2][0] == "sleep 0.5"
