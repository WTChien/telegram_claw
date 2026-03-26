import os
import subprocess
import sys


def main() -> None:
    host = os.getenv("API_HOST", "0.0.0.0")
    port = os.getenv("API_PORT", "8000")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
