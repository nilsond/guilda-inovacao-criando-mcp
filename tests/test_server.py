"""Testes de integração da superfície MCP usando o cliente em memória do SDK v2."""

import pytest
from mcp.client import Client

pytestmark = pytest.mark.anyio

TOOLS_ESPERADAS = {
    "listar_produtos",
    "buscar_produto_por_id",
    "verificar_estoque",
    "adicionar_ao_carrinho",
    "remover_do_carrinho",
    "ver_carrinho",
    "finalizar_pedido",
}


def _texto(resultado) -> str:
    return " ".join(getattr(c, "text", "") for c in resultado.content)


async def test_lista_as_sete_tools_com_descricao(server) -> None:
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == TOOLS_ESPERADAS
    assert all(t.description for t in tools)
    listar = next(t for t in tools if t.name == "listar_produtos")
    assert listar.annotations is not None and listar.annotations.read_only_hint is True
    assert listar.output_schema is not None


async def test_listar_produtos_retorna_structured_content(server) -> None:
    async with Client(server) as client:
        resultado = await client.call_tool("listar_produtos", {"categoria": "casacos"})
    assert not resultado.is_error
    assert resultado.structured_content["categoria_filtro"] == "Casacos"
    assert resultado.structured_content["total"] == 2


async def test_erro_de_dominio_vira_is_error(server) -> None:
    async with Client(server) as client:
        resultado = await client.call_tool("buscar_produto_por_id", {"produto_id": 999})
    assert resultado.is_error
    assert "não encontrado" in _texto(resultado)


async def test_fluxo_completo_de_compra(server) -> None:
    async with Client(server) as client:
        add = await client.call_tool(
            "adicionar_ao_carrinho", {"session_id": "demo", "produto_id": 6, "quantidade": 2, "tamanho": "m"}
        )
        assert not add.is_error, _texto(add)

        estoque = await client.call_tool("verificar_estoque", {"produto_id": 6, "tamanho": "M"})
        assert estoque.structured_content["disponivel"] == 4
        assert estoque.structured_content["reservado"] == 2

        remover = await client.call_tool(
            "remover_do_carrinho", {"session_id": "demo", "produto_id": 6, "tamanho": "M", "quantidade": 1}
        )
        assert remover.structured_content["carrinho"]["quantidade_itens"] == 1

        carrinho = await client.call_tool("ver_carrinho", {"session_id": "demo"})
        assert carrinho.structured_content["total_formatado"] == "R$ 289,90"

        excesso = await client.call_tool(
            "adicionar_ao_carrinho", {"session_id": "demo", "produto_id": 6, "quantidade": 99, "tamanho": "M"}
        )
        assert excesso.is_error
        assert "Estoque insuficiente" in _texto(excesso)

        pedido = await client.call_tool(
            "finalizar_pedido",
            {"session_id": "demo", "endereco_entrega": "Av. Paulista, 1000 - Bela Vista, São Paulo/SP"},
        )
        assert not pedido.is_error, _texto(pedido)
        assert pedido.structured_content["status"] == "confirmado"

        final = await client.call_tool("verificar_estoque", {"produto_id": 6, "tamanho": "M"})
        assert final.structured_content["estoque_fisico"] == 5
        assert final.structured_content["reservado"] == 0

        vazio = await client.call_tool("finalizar_pedido", {"session_id": "demo", "endereco_entrega": "Av. Paulista, 1000"})
        assert vazio.is_error
        assert "vazio" in _texto(vazio)


async def test_resource_politica_trocas(server) -> None:
    async with Client(server) as client:
        recursos = (await client.list_resources()).resources
        assert any(str(r.uri) == "ecommerce://politica-trocas" for r in recursos)
        conteudo = await client.read_resource("ecommerce://politica-trocas")
    texto = conteudo.contents[0].text
    assert "troca" in texto.lower()
    assert "7 dias" in texto


async def test_prompt_recomendar_look(server) -> None:
    async with Client(server) as client:
        prompts = (await client.list_prompts()).prompts
        assert any(p.name == "recomendar_look" for p in prompts)
        resultado = await client.get_prompt("recomendar_look", {"ocasiao": "casamento de dia", "estilo": "clássico"})
    texto = resultado.messages[0].content.text
    assert "casamento de dia" in texto
    assert "clássico" in texto
    assert "Polo Piquet Clássica" in texto
