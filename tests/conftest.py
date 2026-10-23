import pytest

from vestuario_mcp import Loja, build_server


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def loja() -> Loja:
    return Loja()


@pytest.fixture
def server(loja: Loja):
    return build_server(loja)
