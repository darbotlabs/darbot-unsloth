# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved.

import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests.studio.studiobench.runtime import types as runtime_types
from tests.studio.studiobench.runtime.types import OutDirLock


def test_permission_denied_does_not_authorize_removing_a_live_posix_marker(monkeypatch):
    def denied(pid, signal):
        raise PermissionError("query denied")

    monkeypatch.setattr(runtime_types, "os", SimpleNamespace(name = "posix", kill = denied))
    assert OutDirLock._alive(123)


@pytest.mark.skipif(sys.platform != "win32", reason = "native Windows process handle query")
@pytest.mark.parametrize("exit_code", [0, 259])
def test_windows_liveness_observes_an_owned_process_without_signalling(monkeypatch, exit_code):
    def must_not_signal(*args):
        raise AssertionError("a liveness query must never signal a Windows process")

    monkeypatch.setattr(os, "kill", must_not_signal)
    assert OutDirLock._alive(os.getpid())
    with subprocess.Popen(
        [
            sys.executable, "-c",
            f"import sys; print('ready',flush=True); sys.stdin.read(1); sys.exit({exit_code})",
        ],
        stdin = subprocess.PIPE, stdout = subprocess.PIPE, text = True,
    ) as child:
        try:
            assert child.stdout.readline().strip() == "ready"
            assert OutDirLock._alive(child.pid)
            child.stdin.write("x")
            child.stdin.flush()
            assert child.wait(timeout = 10) == exit_code
            assert not OutDirLock._alive(child.pid)
        finally:
            if child.poll() is None:
                child.stdin.close()
                child.wait(timeout = 10)


@pytest.mark.skipif(sys.platform != "win32", reason = "Windows kernel query error contracts")
@pytest.mark.parametrize(
    "handle,last_error,wait_result,alive",
    [
        (0, 87, None, False),
        (0, 5, None, True),
        (0, 6, None, True),
        (42, 0, 258, True),
        (42, 0, 0, False),
        (42, 0, 0xFFFFFFFF, True),
    ],
)
def test_windows_liveness_is_query_only_and_fails_closed(monkeypatch, handle, last_error, wait_result, alive):
    import ctypes

    calls = []

    def open_process(access, inherit, pid):
        calls.append(("open", access, inherit, pid))
        return handle

    def wait(process, timeout):
        calls.append(("wait", process, timeout))
        return wait_result

    def close(process):
        calls.append(("close", process))
        return True

    kernel = SimpleNamespace(OpenProcess = open_process, WaitForSingleObject = wait, CloseHandle = close)
    monkeypatch.setattr(ctypes, "WinDLL", lambda *args, **kwargs: kernel)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: last_error)
    assert OutDirLock._alive(123) is alive
    assert calls[0] == ("open", 0x00100000, False, 123)
    assert calls[1:] == ([("wait", handle, 0), ("close", handle)] if handle else [])
    assert not OutDirLock._alive(0)
    assert not OutDirLock._alive(-1)
    assert not OutDirLock._alive(0x100000000)
    assert sum(call[0] == "open" for call in calls) == 1


@pytest.mark.skipif(sys.platform != "win32", reason = "Windows mandatory byte-range locking")
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_a_new_reader_does_not_bypass_an_old_windows_mutex(tmp_path, newline):
    import msvcrt

    marker = tmp_path / ".running.lock"
    old_record = f"{os.getpid()} oldsession{newline}".encode()
    fd = os.open(marker, os.O_CREAT | os.O_RDWR | os.O_BINARY, 0o644)
    try:
        os.write(fd, old_record)
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        try:
            with pytest.raises(SystemExit, match = "another run is still holding it"):
                OutDirLock.take(tmp_path, "contender")
        finally:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    finally:
        os.close(fd)
    assert marker.read_bytes() == old_record
    assert OutDirLock._read_marker(marker) == ("oldsession", os.getpid())
    with_new_lock = OutDirLock.take(tmp_path, "newsession")
    try:
        assert OutDirLock._read_marker(marker) == ("newsession", os.getpid())
        old_reader = os.open(marker, os.O_RDWR | os.O_BINARY)
        try:
            with pytest.raises(OSError):
                msvcrt.locking(old_reader, msvcrt.LK_NBLCK, 1)
        finally:
            os.close(old_reader)
    finally:
        with_new_lock.release()
    assert marker.read_bytes() == b""


@pytest.mark.skipif(sys.platform != "win32", reason = "Windows versioned owner-record protocol")
@pytest.mark.parametrize(
    "record",
    [
        b"\0UNSLOTH_LOCK_V1 123 partial",
        b"\0UNSLOTH_LOCK_V1 123\n",
        b"\0UNSLOTH_LOCK_V1 not-a-pid session\n",
    ],
)
def test_incomplete_or_invalid_windows_owner_records_are_not_named(tmp_path, record):
    marker = tmp_path / ".running.lock"
    marker.write_bytes(record)
    assert OutDirLock._read_marker(marker) is None
