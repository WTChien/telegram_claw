import asyncio
import io
import json
import subprocess
from typing import List, Tuple

from PIL import Image

from backend.utils.logger import get_logger

logger = get_logger()


class ComputerControl:
    async def take_screenshots(self) -> List[bytes]:
        """Take screenshots for each display and return PNG bytes per display."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._capture_display_images_sync)

    async def take_screenshot(self) -> bytes:
        """Take a screenshot and return PNG bytes."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._screenshot_sync)

    def _capture_display_images_sync(self) -> List[bytes]:
        import os
        import tempfile

        def detect_display_ids() -> List[int]:
            try:
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType", "-json"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                payload = json.loads(result.stdout)
                displays = payload.get("SPDisplaysDataType", [])
                count = 0
                for adapter in displays:
                    count += len(adapter.get("spdisplays_ndrvs", []))
                if count > 0:
                    return list(range(1, count + 1))
            except Exception:
                logger.warning("Failed to detect displays via system_profiler", exc_info=True)

            return [1]

        def capture_one(display_id: int) -> bytes:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                cmd = ["screencapture", "-x"]
                if display_id > 0:
                    cmd.extend(["-D", str(display_id)])
                cmd.append(tmp_path)
                result = subprocess.run(
                    cmd,
                    check=False,
                    timeout=10,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                if result.returncode != 0:
                    err = result.stderr.decode(errors="replace").strip()
                    raise subprocess.CalledProcessError(
                        result.returncode, cmd, stderr=err
                    )
                with open(tmp_path, "rb") as f:
                    return f.read()
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        display_images: List[bytes] = []
        seen_hashes = set()

        for display_id in detect_display_ids():
            try:
                raw = capture_one(display_id)
            except Exception:
                continue
            digest = hash(raw)
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            display_images.append(raw)

        if display_images:
            return display_images

        return [capture_one(0)]

    def _screenshot_sync(self) -> bytes:
        display_images = self._capture_display_images_sync()

        if len(display_images) == 1:
            return display_images[0]

        images = [Image.open(io.BytesIO(raw)).convert("RGB") for raw in display_images]
        total_width = sum(img.width for img in images)
        max_height = max(img.height for img in images)

        canvas = Image.new("RGB", (total_width, max_height), color=(20, 20, 20))
        x_offset = 0
        for img in images:
            canvas.paste(img, (x_offset, 0))
            x_offset += img.width

        output = io.BytesIO()
        canvas.save(output, format="PNG")
        return output.getvalue()

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
