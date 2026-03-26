import asyncio
import io
import subprocess
from typing import Tuple

from backend.utils.logger import get_logger

logger = get_logger()


class ComputerControl:
    async def take_screenshot(self) -> bytes:
        """Take a screenshot and return PNG bytes."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._screenshot_sync)

    def _screenshot_sync(self) -> bytes:
        # macOS: use built-in screencapture command (no extra permissions needed for file)
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            subprocess.run(["screencapture", "-x", tmp_path], check=True, timeout=10)
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    async def run_command(self, cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Run a shell command and return (returncode, stdout, stderr)."""
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")
        except asyncio.TimeoutError:
            proc.kill()
            return -1, "", "指令逾時"

    async def type_text(self, text: str) -> None:
        """Type text using osascript (no extra permissions on macOS)."""
        script = f'tell application "System Events" to keystroke "{text}"'
        await self.run_command(f"osascript -e '{script}'")

    async def open_url(self, url: str) -> None:
        """Open a URL in the default browser."""
        await self.run_command(f"open '{url}'")

    async def open_app(self, app_name: str) -> None:
        """Open a macOS application by name."""
        await self.run_command(f"open -a '{app_name}'")


computer = ComputerControl()
