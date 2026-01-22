# llama_multiserver.py – rewired to work with EthosSandbox

"""
This module implements a lightweight wrapper around the `llama-server`
executable.  It is deliberately minimal so it can be imported from any
Python program (including the sandbox UI) without pulling in heavy GUI
dependencies.

Public API
----------
* :class:`LlamaServer` – represents a single server instance.
* :func:`port_open(port)` – quick helper that tests if a TCP port is
  already listening on localhost.
"""

# ------------------------------------------------------------------
# Imports -------------------------------------------------------------
import sys
import subprocess          # needed by the UI when launching servers
import threading           # for stdout streaming
import socket              # to probe ports
from pathlib import Path   # for file‑path sanity checks

# ------------------------------------------------------------------
# Configuration --------------------------------------------------------
DEFAULT_HOST = "127.0.0.1"

# ------------------------------------------------------------------
# Utilities ------------------------------------------------------------
def port_open(port: int) -> bool:
    """
    Return ``True`` if *port* is accepting TCP connections on
    :data:`DEFAULT_HOST`.  The function simply tries to open a socket and
    closes it immediately.

    Parameters
    ----------
    port : int
        Port number to test.
    """
    try:
        with socket.create_connection((DEFAULT_HOST, port), timeout=1):
            return True
    except Exception:   # pragma: no cover – the exception type is irrelevant
        return False


# ------------------------------------------------------------------
# Server Record --------------------------------------------------------
class LlamaServer:
    """
    Lightweight representation of a running or planned llama‑server.

    Attributes
    ----------
    binary : str
        Path to the ``llama-server`` executable.
    model  : str
        Path to the `.gguf` model file.
    port   : int
        TCP port on which this instance should listen.
    ctx    : int
        Context size (the ``--ctx-size`` argument).
    process : subprocess.Popen | None
        The running process, if any.
    """

    def __init__(self, binary: str, model: str, port: int, ctx: int):
        self.binary = binary
        self.model  = model
        self.port   = port
        self.ctx    = ctx
        self.process: subprocess.Popen | None = None

    # ------------------------------------------------------------------
    def is_running(self) -> bool:
        """Return ``True`` if the underlying process is still alive."""
        return self.process is not None and self.process.poll() is None


# ------------------------------------------------------------------
__all__ = ["LlamaServer", "port_open", "DEFAULT_HOST"]
