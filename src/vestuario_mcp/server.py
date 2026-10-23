"""Superfície MCP do Vestuário MCP: tools, resource e prompt (MCP Python SDK v2 / MCPServer).

No SDK v2 o antigo ``FastMCP`` se chama ``MCPServer`` (``mcp.server.mcpserver``).
Os decorators ``@mcp.tool()``, ``@mcp.resource()`` e ``@mcp.prompt()`` funcionam como antes.
A docstring de cada função vira a descrição que o LLM lê, por isso elas são detalhadas.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.prompts.base import UserMessage
from mcp.types import ToolAnnotations
from pydantic import Field

from vestuario_mcp.data import POLITICA_TROCAS
from vestuario_mcp.models import (
    Carrinho,
    ListaProdutos,
    OperacaoCarrinho,
    Pedido,
    ProdutoDetalhe,
    StatusEstoque,
)
from vestuario_mcp.services import ErroLoja, Loja

INSTRUCOES = """\
Você está conectado ao backend da loja de roupas "Vestuário MCP". Preços em BRL; tamanhos P, M, G e GG.
Fluxo típico de compra:
1. listar_produtos (opcionalmente por categoria: Camisetas, Calças, Casacos, Acessórios, Calçados)
2. buscar_produto_por_id / verificar_estoque para confirmar tamanho e disponibilidade
3. adicionar_ao_carrinho (reserva o estoque) / remover_do_carrinho (devolve a reserva)
4. ver_carrinho para conferir o total
5. finalizar_pedido com o endereço de entrega
Use sempre o mesmo session_id para o mesmo cliente. A política de trocas está no resource
ecommerce://politica-trocas, e o prompt recomendar_look ajuda a montar combinações.
"""

URI_POLITICA_TROCAS = "ecommerce://politica-trocas"

_LEITURA = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
_ESCRITA = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)

# Tipos de parâmetro reutilizados. As descrições entram no input schema das tools.
SessionId = Annotated[
    str,
    Field(description="Identificador do carrinho do cliente, ex.: 'demo'. Use o mesmo valor em toda a compra."),
]
ProdutoId = Annotated[int, Field(description="ID numérico do produto, obtido em listar_produtos.")]
TamanhoParam = Annotated[str, Field(description="Tamanho da peça: P, M, G ou GG.")]


@contextmanager
def _erros_de_dominio() -> Iterator[None]:
    """Converte erros de negócio em ``ToolError``.

    O ``ToolError`` vira um resultado com ``is_error=True``, que o LLM lê para se corrigir.
    """
    try:
        yield
    except ErroLoja as erro:
        raise ToolError(str(erro)) from erro


def build_server(loja: Loja | None = None) -> MCPServer:
    """Cria o servidor MCP ligado a uma instância de ``Loja``. Sem argumento, usa uma loja nova."""
    loja = loja if loja is not None else Loja()
    mcp = MCPServer("Vestuário MCP", instructions=INSTRUCOES, version="0.1.0")

    # ------------------------------------------------------------------ tools: catálogo

    @mcp.tool(annotations=_LEITURA)
    def listar_produtos(
        categoria: Annotated[
            str | None,
            Field(description="Filtro opcional: Camisetas, Calças, Casacos, Acessórios ou Calçados. Omita para listar tudo."),
        ] = None,
    ) -> ListaProdutos:
        """Lista os produtos do catálogo da loja Vestuário MCP.

        Use esta tool para descobrir o que existe à venda antes de recomendar ou adicionar itens.
        Para cada produto vêm: id, nome, categoria, preço em BRL, tamanhos vendidos, cores e
        unidades disponíveis somando todos os tamanhos.

        Args:
            categoria: filtro opcional por categoria. Não diferencia maiúsculas nem acentos
                ("calcas" também funciona).

        Returns:
            Objeto com o filtro aplicado, o total de produtos e a lista de produtos.

        Erros:
            Categoria inexistente. A mensagem lista as categorias válidas.
        """
        with _erros_de_dominio():
            return loja.listar_produtos(categoria)

    @mcp.tool(annotations=_LEITURA)
    def buscar_produto_por_id(produto_id: ProdutoId) -> ProdutoDetalhe:
        """Retorna todos os detalhes de um produto: descrição, cores, tamanhos, preço e disponibilidade por tamanho.

        Args:
            produto_id: ID do produto, obtido em listar_produtos.

        Returns:
            Detalhes do produto, incluindo `disponivel_por_tamanho` (estoque físico menos reservas).

        Erros:
            Produto não encontrado. A mensagem lista os IDs existentes.
        """
        with _erros_de_dominio():
            return loja.buscar_produto(produto_id)

    @mcp.tool(annotations=_LEITURA)
    def verificar_estoque(produto_id: ProdutoId, tamanho: TamanhoParam) -> StatusEstoque:
        """Consulta se há estoque disponível de um produto em um tamanho específico.

        Mostra o estoque físico, quantas unidades estão reservadas em carrinhos e quantas ainda
        podem ser adicionadas (`disponivel`). Consulte antes de adicionar ao carrinho.

        Args:
            produto_id: ID do produto.
            tamanho: P, M, G ou GG (aceita minúsculas).

        Returns:
            Situação do estoque com `em_estoque` (bool) e uma mensagem legível.

        Erros:
            Produto não encontrado; tamanho fora da grade ou não vendido para esse produto.
        """
        with _erros_de_dominio():
            return loja.verificar_estoque(produto_id, tamanho)

    # ------------------------------------------------------------------ tools: carrinho

    @mcp.tool(annotations=_ESCRITA)
    def adicionar_ao_carrinho(
        session_id: SessionId,
        produto_id: ProdutoId,
        quantidade: Annotated[int, Field(description="Quantidade de unidades, inteiro maior que zero.")],
        tamanho: TamanhoParam,
    ) -> OperacaoCarrinho:
        """Adiciona um item ao carrinho do cliente e RESERVA as unidades no estoque.

        A reserva diminui a disponibilidade para outros clientes até o pedido ser finalizado ou o
        item ser removido. Adicionar de novo o mesmo produto e tamanho soma as quantidades.

        Args:
            session_id: identificador do carrinho do cliente.
            produto_id: ID do produto.
            quantidade: unidades a adicionar (> 0).
            tamanho: P, M, G ou GG.

        Returns:
            Mensagem de confirmação e o carrinho atualizado com o total.

        Erros:
            Produto não encontrado; tamanho inválido ou indisponível para o produto; quantidade <= 0;
            estoque insuficiente (a mensagem informa quantas unidades estão disponíveis).
        """
        with _erros_de_dominio():
            return loja.adicionar_ao_carrinho(session_id, produto_id, quantidade, tamanho)

    @mcp.tool(annotations=_ESCRITA)
    def remover_do_carrinho(
        session_id: SessionId,
        produto_id: ProdutoId,
        tamanho: TamanhoParam,
        quantidade: Annotated[
            int | None,
            Field(description="Unidades a remover. Omita para remover o item inteiro."),
        ] = None,
    ) -> OperacaoCarrinho:
        """Remove um item do carrinho, inteiro ou em parte, e devolve a reserva ao estoque.

        Args:
            session_id: identificador do carrinho do cliente.
            produto_id: ID do produto que está no carrinho.
            tamanho: tamanho do item no carrinho.
            quantidade: unidades a remover; se omitido, remove a linha inteira.

        Returns:
            Mensagem de confirmação e o carrinho atualizado.

        Erros:
            Item não está no carrinho; quantidade <= 0 ou maior que a quantidade no carrinho.
        """
        with _erros_de_dominio():
            return loja.remover_do_carrinho(session_id, produto_id, tamanho, quantidade)

    @mcp.tool(annotations=_LEITURA)
    def ver_carrinho(session_id: SessionId) -> Carrinho:
        """Exibe o conteúdo atual do carrinho de um cliente e calcula o valor total.

        Args:
            session_id: identificador do carrinho do cliente.

        Returns:
            Itens com preço unitário e subtotal, quantidade total de unidades e total em BRL.
            Uma sessão sem itens devolve carrinho vazio (total R$ 0,00).
        """
        with _erros_de_dominio():
            return loja.ver_carrinho(session_id)

    @mcp.tool(annotations=_ESCRITA)
    def finalizar_pedido(
        session_id: SessionId,
        endereco_entrega: Annotated[
            str,
            Field(description="Endereço completo: rua, número, bairro, cidade/UF e CEP."),
        ],
    ) -> Pedido:
        """Finaliza a compra: converte o carrinho em pedido, baixa o estoque e limpa o carrinho.

        Confirme o carrinho com o cliente (ver_carrinho) antes de chamar esta tool.

        Args:
            session_id: identificador do carrinho do cliente.
            endereco_entrega: endereço completo de entrega.

        Returns:
            Pedido confirmado com número, itens, total, endereço e data/hora.

        Erros:
            Carrinho vazio; endereço vazio ou incompleto.
        """
        with _erros_de_dominio():
            return loja.finalizar_pedido(session_id, endereco_entrega)

    # ------------------------------------------------------------------ resource

    @mcp.resource(
        URI_POLITICA_TROCAS,
        name="politica-trocas",
        title="Política de Trocas e Devoluções",
        description="Prazos, condições, itens não trocáveis e regras de reembolso da Vestuário MCP.",
        mime_type="text/markdown",
    )
    def politica_trocas() -> str:
        """Política de trocas e devoluções da loja, em Markdown."""
        return POLITICA_TROCAS

    # ------------------------------------------------------------------ prompt

    @mcp.prompt(title="Recomendar look")
    def recomendar_look(
        ocasiao: Annotated[str, Field(description="Ocasião do look, ex.: 'casamento de dia', 'entrevista', 'happy hour'.")],
        estilo: Annotated[
            str | None,
            Field(description="Estilo preferido (opcional), ex.: 'minimalista', 'streetwear', 'clássico'."),
        ] = None,
    ) -> list[UserMessage]:
        """Assistente de estilo: monta combinações de roupas usando só as peças do catálogo da loja."""
        preferencia = f" O cliente prefere um estilo **{estilo}**." if estilo else ""
        texto = f"""\
Você é o consultor de estilo da loja Vestuário MCP.
Monte de 2 a 3 looks para a ocasião **{ocasiao}**.{preferencia}

Regras:
- Use SOMENTE peças do catálogo abaixo e cite o ID de cada uma.
- Cada look deve ter uma parte de cima e uma de baixo (ou um casaco por cima), e pode ter calçado e acessório.
- Sugira cores que combinem, entre as cores disponíveis de cada peça.
- Mostre o valor total estimado de cada look em BRL.
- Explique em uma frase por que o look funciona para a ocasião.
- Antes de recomendar um tamanho, sugira verificar_estoque. Se o cliente aprovar, ofereça
  adicionar_ao_carrinho (pergunte o session_id e o tamanho).

Catálogo atual:
{loja.resumo_catalogo()}
"""
        return [UserMessage(texto)]

    return mcp
