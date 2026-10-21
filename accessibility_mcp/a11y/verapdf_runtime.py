"""Prepara o veraPDF oficial na pasta do usuario, com versao e hash fixos."""

from __future__ import annotations

import asyncio
import hashlib
import io
import shutil
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

import httpx

from . import learn
from .provisioning import auto_install_enabled

VERSION = "1.30.1"
URL = f"https://software.verapdf.org/releases/1.30/verapdf-greenfield-{VERSION}-installer.zip"
SHA256 = "9f03fc5da454348329f4054256351aa6c6a91683329978e8294f21fe8a5d7abc"
_LOCK = asyncio.Lock()


def cached_jar() -> Path:
    return learn.store_path() / "tools" / f"verapdf-{VERSION}" / "app" / "bin" / f"cli-{VERSION}.jar"


async def ensure() -> Path | None:
    jar = cached_jar()
    if jar.is_file():
        return jar
    java = shutil.which("java")
    if not java or not auto_install_enabled():
        return None
    async with _LOCK:
        if jar.is_file():
            return jar
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            response = await client.get(URL)
            response.raise_for_status()
        data = response.content
        if hashlib.sha256(data).hexdigest() != SHA256:
            raise ValueError("O hash do instalador veraPDF diverge da versao fixada; nada foi executado.")
        with ZipFile(io.BytesIO(data)) as archive:
            names = [n for n in archive.namelist() if n.endswith(".jar")]
            if len(names) != 1:
                raise ValueError("O pacote veraPDF nao contem um instalador unico.")
            installer = archive.read(names[0])
        target = jar.parent.parent
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="a11y-verapdf-") as temp:
            directory = Path(temp)
            (directory / "installer.jar").write_bytes(installer)
            config = f'''<AutomatedInstallation langpack="eng">
<com.izforge.izpack.panels.htmlhello.HTMLHelloPanel id="welcome"/>
<com.izforge.izpack.panels.target.TargetPanel id="install_dir"><installpath>{escape(target.as_posix())}</installpath></com.izforge.izpack.panels.target.TargetPanel>
<com.izforge.izpack.panels.packs.PacksPanel id="sdk_pack_select">
<pack index="0" name="veraPDF GUI" selected="true"/><pack index="1" name="veraPDF Mac and *nix Scripts" selected="false"/>
<pack index="2" name="veraPDF Corpus and Validation model" selected="false"/><pack index="3" name="veraPDF Documentation" selected="false"/>
<pack index="4" name="veraPDF Sample Plugins" selected="false"/></com.izforge.izpack.panels.packs.PacksPanel>
<com.izforge.izpack.panels.install.InstallPanel id="install"/><com.izforge.izpack.panels.finish.FinishPanel id="finish"/></AutomatedInstallation>'''
            (directory / "install.xml").write_text(config, encoding="utf-8")
            process = await asyncio.create_subprocess_exec(java, "-jar", str(directory / "installer.jar"), str(directory / "install.xml"),
                                                           stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                await process.communicate()
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            if process.returncode != 0 or not jar.is_file():
                raise ValueError("A instalacao do veraPDF nao terminou corretamente.")
        return jar
