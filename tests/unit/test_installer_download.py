"""Unit tests for the https-only installer download (R0.11, 02-10; IN-06 and A-1, 02-15).

The fetched script is executed with ``sh``, so a non-https URL is a scheme-downgrade
code-execution path (ASVS V12), and a redirect can downgrade a fetch that started as https.
Every case runs against an in-memory network: the stock ``HTTPSHandler.https_open`` and
``HTTPHandler.http_open`` are replaced by plain functions with ``monkeypatch.setattr``, so every
opener, whether ``urlopen`` or the redirect-refusing one, reaches the route table and no socket
opens, red or green. No handler subclass is defined, so vulture has nothing to report.
``tempfile.tempdir`` points at ``tmp_path``, so nothing lands in the system temp directory.
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import http.client
import io
import os
import tempfile
import urllib.error
import urllib.request
import urllib.response
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest

from kitty_setup import installer


class _Served(urllib.response.addinfourl):
    """An in-memory response. ``msg`` is read by ``HTTPErrorProcessor`` in the stock opener."""

    msg = "OK"


class _Network:
    """Routes ``url -> (status, body, Location)``, and every URL each scheme was asked for."""

    def __init__(self) -> None:
        self.routes: dict[str, tuple[int, bytes, str | None]] = {}
        self.https_seen: list[str] = []
        self.http_seen: list[str] = []

    def serve(
        self, url: str, body: bytes = b"", *, code: int = 200, location: str | None = None
    ) -> None:
        self.routes[url] = (code, body, location)

    def respond(self, url: str) -> urllib.response.addinfourl:
        route = self.routes.get(url)
        if route is None:
            raise urllib.error.URLError(f"no route to {url} (fake network down)")
        code, body, location = route
        headers = http.client.HTTPMessage()
        if location is not None:
            headers["Location"] = location
        return _Served(io.BytesIO(body), headers, url, code)


@pytest.fixture(autouse=True)
def network(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _Network:
    net = _Network()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    def serve_https(handler: object, req: urllib.request.Request) -> urllib.response.addinfourl:
        del handler
        net.https_seen.append(req.full_url)
        return net.respond(req.full_url)

    def serve_http(handler: object, req: urllib.request.Request) -> urllib.response.addinfourl:
        del handler
        net.http_seen.append(req.full_url)
        marker = b"#!/bin/sh\necho EVIL-over-plain-http\n"
        return _Served(io.BytesIO(marker), http.client.HTTPMessage(), req.full_url, 200)

    monkeypatch.setattr(urllib.request.HTTPSHandler, "https_open", serve_https)
    monkeypatch.setattr(urllib.request.HTTPHandler, "http_open", serve_http)
    return net


@pytest.fixture
def mkstemp_fds(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[int]]:
    """Record every fd ``tempfile.mkstemp`` returns; close any still open at teardown."""
    fds: list[int] = []
    real_mkstemp = tempfile.mkstemp

    def recording(*, prefix: str, suffix: str) -> tuple[int, str]:
        # The installer's only call shape: keyword prefix and suffix.
        fd, name = real_mkstemp(prefix=prefix, suffix=suffix)
        fds.append(fd)
        return fd, name

    monkeypatch.setattr(tempfile, "mkstemp", recording)
    yield fds
    for fd in fds:
        with contextlib.suppress(OSError):
            os.close(fd)


def _bind_download() -> Callable[[str], Path]:
    # Private name reached through vars() so pyright strict reports no reportPrivateUsage.
    return cast(Callable[[str], Path], vars(installer)["_download_installer"])


def _installer_leak() -> list[str]:
    return glob.glob(str(Path(tempfile.gettempdir()) / "kitty-installer-*.sh"))


def _fd_is_closed(fd: int) -> bool:
    try:
        os.fstat(fd)
    except OSError:
        return True
    return False


@pytest.mark.parametrize(
    "url",
    [
        "http://example.invalid/installer.sh",
        "file:///nonexistent/installer.sh",
        "ftp://example.invalid/installer.sh",
    ],
)
def test_download_scheme_rejects_non_https(url: str, tmp_path: Path, network: _Network) -> None:
    """A non-https URL is rejected with a ValueError naming the scheme — no file, no fetch."""
    download = _bind_download()

    with pytest.raises(ValueError, match="https"):
        download(url)

    assert network.https_seen == [] and network.http_seen == [], "the rejected URL was fetched"
    leaked = list(tmp_path.glob("kitty-installer-*")) + _installer_leak()
    assert leaked == [], "a rejected URL must not create a temporary file"


def test_guard_download_installer_url_fetches(tmp_path: Path, network: _Network) -> None:
    """``INSTALLER_URL`` is https and still downloads; the returned file holds the bytes."""
    payload = b"#!/bin/sh\necho kitty\n"
    network.serve(installer.INSTALLER_URL, payload)
    download = _bind_download()

    result = download(installer.INSTALLER_URL)

    assert network.https_seen == [installer.INSTALLER_URL], "the pinned https URL must be fetched"
    assert result.is_file()
    assert result.read_bytes() == payload
    assert result.parent == tmp_path


def test_download_redirect_to_http_is_refused(tmp_path: Path, network: _Network) -> None:
    """An https fetch that redirects to plain http is refused before any http request."""
    network.serve(
        installer.INSTALLER_URL,
        code=302,
        location="http://sw.kovidgoyal.net/kitty/installer.sh",
    )
    download = _bind_download()

    with pytest.raises(ValueError, match="https"):
        download(installer.INSTALLER_URL)

    assert network.http_seen == [], "the plain-http hop must never be requested"
    assert list(tmp_path.glob("kitty-installer-*")) == []
    assert _installer_leak() == []


def test_download_failure_leaves_no_temp_file(
    tmp_path: Path, network: _Network, mkstemp_fds: list[int]
) -> None:
    """A failed fetch unlinks its temp file and closes the fd that ``mkstemp`` returned."""
    download = _bind_download()

    with pytest.raises(urllib.error.URLError):
        download(installer.INSTALLER_URL)

    assert mkstemp_fds, "mkstemp must have run, or the fd half of this case proves nothing"
    assert list(tmp_path.glob("kitty-installer-*")) == [], "a failed fetch left its temp file"
    assert _installer_leak() == []
    assert all(_fd_is_closed(fd) for fd in mkstemp_fds), "a failed fetch leaked its mkstemp fd"


def test_download_closes_its_temp_fd(network: _Network, mkstemp_fds: list[int]) -> None:
    """After a successful download the fd that ``mkstemp`` returned is closed."""
    network.serve(installer.INSTALLER_URL, b"#!/bin/sh\necho kitty\n")
    download = _bind_download()

    download(installer.INSTALLER_URL)

    assert mkstemp_fds, "mkstemp must have run, or this case proves nothing"
    assert all(_fd_is_closed(fd) for fd in mkstemp_fds), "a successful download leaked its fd"


def test_cli_install_value_error_is_one_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A refused URL or redirect ends in one ``install failed:`` stderr line and exit 1."""

    def refused(**kwargs: object) -> None:
        del kwargs
        raise ValueError("installer download redirected to a non-https URL: http://x.invalid/i.sh")

    monkeypatch.setattr(installer, "install", refused)

    rc = installer.cli_install(argparse.Namespace(dest=tmp_path, no_config=True))

    assert rc == 1
    err_lines = capsys.readouterr().err.splitlines()
    assert len(err_lines) == 1, err_lines
    assert err_lines[0].startswith("install failed: ")


@pytest.mark.parametrize("kind", ["absolute", "relative"])
def test_download_redirect_https_to_https_is_followed(kind: str, network: _Network) -> None:
    """An https redirect to https, absolute or relative, is still followed to its body."""
    body = b"#!/bin/sh\necho kitty\n"
    if kind == "absolute":
        target = "https://mirror.example/installer.sh"
        location = target
    else:
        target = "https://sw.kovidgoyal.net/kitty/installer-v2.sh"
        location = "installer-v2.sh"
    network.serve(installer.INSTALLER_URL, code=302, location=location)
    network.serve(target, body)
    download = _bind_download()

    result = download(installer.INSTALLER_URL)

    assert network.https_seen == [installer.INSTALLER_URL, target]
    assert network.http_seen == []
    assert result.read_bytes() == body
