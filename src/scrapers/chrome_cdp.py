"""Helper CDP: Chrome real com perfil temporário (padrão validado nas POCs
de 2026-09-02 contra o Akamai — Smiles e Azul). NÃO usa o perfil pessoal."""

import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from playwright.async_api import Browser, async_playwright

from src.config import find_chrome


class RealChrome:
    """Lança Chrome real (perfil temp + debug port) e expõe conexão CDP.

    Uso:
        async with RealChrome(port=9301) as chrome:
            page = await chrome.page()

    driver: "playwright" (padrão) ou "patchright" — patchright corrige os
    vazamentos de CDP que fazem o Google degradar tarifas p/ automação
    (evidência 2026-09-03/05).
    """

    def __init__(self, port: int, driver: str = "playwright"):
        self.port = port
        self.driver = driver
        self._proc: subprocess.Popen | None = None
        self._profile: Path | None = None
        self._pw = None
        self._browser: Browser | None = None

    async def __aenter__(self) -> "RealChrome":
        chrome = find_chrome()
        self._profile = Path(tempfile.gettempdir()) / f"fm_{uuid.uuid4().hex[:8]}"
        self._proc = subprocess.Popen([
            chrome, f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self._profile}", "--no-first-run",
            "--no-default-browser-check", "--window-size=1920,1080",
            "about:blank"])
        time.sleep(4)
        if self.driver == "patchright":
            from patchright.async_api import async_playwright as pw_start
        else:
            from playwright.async_api import async_playwright as pw_start
        self._pw = await pw_start().start()
        self._browser = await self._pw.chromium.connect_over_cdp(
            f"http://localhost:{self.port}")
        return self

    async def page(self):
        context = self._browser.contexts[0]
        return context.pages[0] if context.pages else await context.new_page()

    async def __aexit__(self, *exc) -> None:
        if self._browser:
            await self._browser.close()  # desconecta (Chrome segue vivo)
        if self._pw:
            await self._pw.stop()
        if self._proc:
            self._proc.terminate()
        # perfil temporário é lixo — limpa na saída
        if self._profile and self._profile.exists():
            import shutil
            shutil.rmtree(self._profile, ignore_errors=True)
