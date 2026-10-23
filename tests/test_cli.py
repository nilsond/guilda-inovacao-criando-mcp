"""Testes da CLI e do transporte HTTP (incluindo o cenário ngrok, simulado pelo header Host)."""

import http.client
import json
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from mcp.client import Client

import server_mcp

RAIZ = Path(__file__).resolve().parents[1]
HOST_NGROK = "demo.ngrok-free.app"


def test_parse_args_padroes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PUBLIC_HOST", raising=False)
    args = server_mcp.parse_args([])
    assert (args.transport, args.host, args.port, args.public_host) == ("stdio", "127.0.0.1", 8000, None)


def test_parse_args_public_host_por_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_HOST", HOST_NGROK)
    args = server_mcp.parse_args(["--transport", "http", "--port", "9000"])
    assert (args.transport, args.port, args.public_host) == ("http", 9000, HOST_NGROK)


@pytest.mark.parametrize(
    "entrada",
    [HOST_NGROK, f"https://{HOST_NGROK}", f"https://{HOST_NGROK}/mcp", f"  {HOST_NGROK}/  "],
)
def test_normalizar_host_publico(entrada: str) -> None:
    assert server_mcp.normalizar_host_publico(entrada) == HOST_NGROK


def test_allowlist() -> None:
    sem = server_mcp.montar_transport_security(None)
    assert HOST_NGROK not in sem.allowed_hosts
    assert "127.0.0.1:*" in sem.allowed_hosts

    com = server_mcp.montar_transport_security(f"https://{HOST_NGROK}/")
    assert HOST_NGROK in com.allowed_hosts
    assert f"https://{HOST_NGROK}" in com.allowed_origins
    assert com.enable_dns_rebinding_protection


# ---------------------------------------------------------------- HTTP real (subprocesso)


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _subir_servidor(*extra: str) -> tuple[subprocess.Popen[bytes], int]:
    porta = _porta_livre()
    proc = subprocess.Popen(
        [sys.executable, str(RAIZ / "server_mcp.py"), "--transport", "http", "--port", str(porta), *extra],
        cwd=RAIZ,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    limite = time.monotonic() + 20
    while time.monotonic() < limite:
        try:
            with socket.create_connection(("127.0.0.1", porta), timeout=0.2):
                return proc, porta
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError("Servidor HTTP não subiu a tempo")


@pytest.fixture
def servidor_http() -> Iterator[int]:
    proc, porta = _subir_servidor()
    yield porta
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture
def servidor_http_ngrok() -> Iterator[int]:
    proc, porta = _subir_servidor("--public-host", HOST_NGROK)
    yield porta
    proc.terminate()
    proc.wait(timeout=10)


def _post_initialize(porta: int, host_header: str) -> int:
    corpo = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "teste", "version": "0"},
            },
        }
    )
    conn = http.client.HTTPConnection("127.0.0.1", porta, timeout=10)
    try:
        conn.request(
            "POST",
            "/mcp",
            body=corpo,
            headers={
                "Host": host_header,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        return conn.getresponse().status
    finally:
        conn.close()


@pytest.mark.anyio
async def test_http_lista_tools(servidor_http: int) -> None:
    async with Client(f"http://127.0.0.1:{servidor_http}/mcp") as client:
        tools = (await client.list_tools()).tools
    assert len(tools) == 7


def test_host_ngrok_bloqueado_sem_public_host(servidor_http: int) -> None:
    assert _post_initialize(servidor_http, HOST_NGROK) == 421


def test_host_ngrok_liberado_com_public_host(servidor_http_ngrok: int) -> None:
    assert _post_initialize(servidor_http_ngrok, HOST_NGROK) == 200
