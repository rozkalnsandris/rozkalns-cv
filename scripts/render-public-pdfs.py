#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "html"
PDFS = {
    "en": HTML / "cv.pdf",
    "de": HTML / "cv-de.pdf",
    "lv": HTML / "cv-lv.pdf",
}


class PdfRenderError(RuntimeError):
    pass


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def find_chrome() -> str:
    for candidate in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
    ):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise PdfRenderError("Chromium/Chrome executable was not found")


@contextlib.contextmanager
def serve_html():
    handler = lambda *args, **kwargs: QuietHandler(  # noqa: E731
        *args, directory=str(HTML), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def render_one(chrome: str, port: int, language: str, output: Path) -> None:
    output.unlink(missing_ok=True)
    query = urlencode({"lang": language, "pdf": "1"})
    url = f"http://127.0.0.1:{port}/?{query}"
    with tempfile.TemporaryDirectory(prefix=f"cv-pdf-{language}-") as user_data:
        command = [
            chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--metrics-recording-only",
            "--mute-audio",
            "--no-first-run",
            "--no-pdf-header-footer",
            "--virtual-time-budget=5000",
            f"--user-data-dir={user_data}",
            f"--print-to-pdf={output}",
            url,
        ]
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60,
            check=False,
        )
    if completed.returncode != 0:
        raise PdfRenderError(
            f"{language} PDF render failed with exit code {completed.returncode}"
        )
    if not output.is_file() or output.stat().st_size < 10_000:
        raise PdfRenderError(f"{language} PDF render did not create a usable file")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="optional directory for previews instead of replacing committed html/cv*.pdf",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chrome = find_chrome()
    targets = PDFS
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        targets = {
            language: args.output_dir / path.name for language, path in PDFS.items()
        }

    with serve_html() as port:
        # Give the server a brief moment to begin accepting connections.
        time.sleep(0.2)
        for language, output in targets.items():
            render_one(chrome, port, language, output)
            print(
                f"PDF_RENDER language={language} bytes={output.stat().st_size} "
                f"path={output.relative_to(ROOT) if output.is_relative_to(ROOT) else output.name}"
            )

    print("PUBLIC_PDF_RENDER=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PdfRenderError, OSError, subprocess.SubprocessError) as error:
        print(f"PUBLIC_PDF_RENDER=FAIL ERROR={error}")
        raise SystemExit(1)
