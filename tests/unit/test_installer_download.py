"""Unit tests for the https scheme check on ``installer._download_installer`` (R0.11, 02-10).

The fetched script is executed with ``sh``, so a non-https URL is a scheme-downgrade
code-execution path (ASVS V12). The fix must reject the URL *before* it creates a file or
opens a connection. Every case replaces ``urllib.request.urlopen`` with a recorder and points
``tempfile.tempdir`` at ``tmp_path``, so no case touches the network and nothing lands in the
system temp directory — red or green.
"""

from __future__ import annotations

import glob
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from kitty_setup import installer


class _Recorder:
    """Stand-in for ``urllib.request.urlopen``; records every call, opens nothing."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, url: str, timeout: int) -> Any:
        self.calls.append(url)
        raise AssertionError(f"urlopen must not be called in this case; got {url!r}")


def _bind_download() -> Callable[[str], Path]:
    # Private name reached through vars() so pyright strict reports no reportPrivateUsage.
    return cast(Callable[[str], Path], vars(installer)["_download_installer"])


def _installer_leak() -> list[str]:
    return glob.glob(str(Path(tempfile.gettempdir()) / "kitty-installer-*.sh"))


@pytest.mark.parametrize(
    "url",
    [
        "http://example.invalid/installer.sh",
        "file:///nonexistent/installer.sh",
        "ftp://example.invalid/installer.sh",
    ],
)
def test_download_scheme_rejects_non_https(
    url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-https URL is rejected with a ValueError naming the scheme — no file, no fetch."""
    recorder = _Recorder()
    monkeypatch.setattr(installer.urllib.request, "urlopen", recorder)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    download = _bind_download()

    with pytest.raises(ValueError, match="https"):
        download(url)

    assert recorder.calls == [], "the rejected URL must not reach urlopen"
    leaked = list(tmp_path.glob("kitty-installer-*")) + _installer_leak()
    assert leaked == [], "a rejected URL must not create a temporary file"


def test_guard_download_installer_url_fetches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``INSTALLER_URL`` is https and still downloads; the returned file holds the bytes."""
    payload = b"#!/bin/sh\necho kitty\n"

    class _Response:
        def __init__(self, data: bytes) -> None:
            self._data = data

        def read(self) -> bytes:
            return self._data

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            pass

    seen: list[str] = []

    def recorder(url: str, timeout: int) -> _Response:
        seen.append(url)
        return _Response(payload)

    monkeypatch.setattr(installer.urllib.request, "urlopen", recorder)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    download = _bind_download()

    result = download(installer.INSTALLER_URL)

    assert seen == [installer.INSTALLER_URL], "the pinned https URL must be fetched"
    assert result.is_file()
    assert result.read_bytes() == payload
    assert result.parent == tmp_path
