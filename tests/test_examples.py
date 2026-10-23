"""Testes dos exemplos em examples/, carregados pelo caminho do arquivo."""

import importlib.util
from pathlib import Path

import pytest
from mcp.client import Client

pytestmark = pytest.mark.anyio

HELLO_PATH = Path(__file__).resolve().parent.parent / "examples" / "hello.py"


def _carregar_hello():
    spec = importlib.util.spec_from_file_location("examples_hello", HELLO_PATH)
    assert spec is not None and spec.loader is not None, f"não foi possível carregar {HELLO_PATH}"
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _texto(resultado) -> str:
    return " ".join(getattr(c, "text", "") for c in resultado.content)


async def test_hello_expoe_tool_somar() -> None:
    hello = _carregar_hello()
    async with Client(hello.mcp) as client:
        tools = (await client.list_tools()).tools
    assert "somar" in {t.name for t in tools}


async def test_hello_somar_retorna_3() -> None:
    hello = _carregar_hello()
    async with Client(hello.mcp) as client:
        resultado = await client.call_tool("somar", {"a": 1, "b": 2})
    assert not resultado.is_error, _texto(resultado)
    assert _texto(resultado).strip() == "3"
    assert resultado.structured_content == {"result": 3}
