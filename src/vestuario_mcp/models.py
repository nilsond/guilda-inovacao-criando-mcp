"""Tipos de domínio e modelos de resposta (Pydantic) do Vestuário MCP.

Os modelos de *resposta* são devolvidos pelas tools. O MCPServer converte cada um
em ``structured_content`` e gera o output schema automaticamente.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class Categoria(StrEnum):
    """Categorias do catálogo."""

    CAMISETAS = "Camisetas"
    CALCAS = "Calças"
    CASACOS = "Casacos"
    ACESSORIOS = "Acessórios"
    CALCADOS = "Calçados"


class Tamanho(StrEnum):
    """Grade de tamanhos da loja."""

    P = "P"
    M = "M"
    G = "G"
    GG = "GG"


def formatar_brl(valor: Decimal) -> str:
    """Formata um valor no padrão brasileiro, ex.: ``Decimal("1299.9")`` -> ``"R$ 1.299,90"``."""
    centavos = valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    texto = f"{centavos:,.2f}"  # 1,299.90
    return "R$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


def para_float(valor: Decimal) -> float:
    """Converte um Decimal monetário para float com 2 casas (apenas para exibição)."""
    return float(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# --------------------------------------------------------------------------- #
# Estado interno
# --------------------------------------------------------------------------- #


class Produto(BaseModel):
    """Produto do catálogo, com estoque físico e reservas por tamanho (estado interno)."""

    id: int
    nome: str
    categoria: Categoria
    preco: Decimal
    tamanhos: list[Tamanho]
    cores: list[str]
    estoque: dict[Tamanho, int]
    reservado: dict[Tamanho, int] = Field(default_factory=dict)
    descricao: str

    def disponivel(self, tamanho: Tamanho) -> int:
        """Quantidade que ainda pode ser adicionada a carrinhos: estoque físico menos reservas."""
        return self.estoque.get(tamanho, 0) - self.reservado.get(tamanho, 0)


# --------------------------------------------------------------------------- #
# Modelos de resposta das tools
# --------------------------------------------------------------------------- #


class ProdutoResumo(BaseModel):
    """Visão resumida de um produto, usada na listagem do catálogo."""

    id: int = Field(description="Identificador do produto.")
    nome: str
    categoria: Categoria
    preco: float = Field(description="Preço unitário em BRL.")
    preco_formatado: str = Field(description="Preço formatado, ex.: R$ 79,90.")
    tamanhos: list[Tamanho]
    cores: list[str]
    disponivel_total: int = Field(description="Unidades disponíveis somando todos os tamanhos.")


class ListaProdutos(BaseModel):
    """Resultado de uma listagem do catálogo."""

    categoria_filtro: Categoria | None = Field(description="Categoria aplicada como filtro, se houver.")
    total: int
    produtos: list[ProdutoResumo]


class ProdutoDetalhe(ProdutoResumo):
    """Todos os detalhes de um produto."""

    descricao: str
    disponivel_por_tamanho: dict[Tamanho, int] = Field(
        description="Unidades disponíveis (estoque físico menos reservas) por tamanho."
    )


class StatusEstoque(BaseModel):
    """Situação do estoque de um produto em um tamanho."""

    produto_id: int
    nome: str
    tamanho: Tamanho
    estoque_fisico: int
    reservado: int = Field(description="Unidades reservadas em carrinhos ainda não finalizados.")
    disponivel: int
    em_estoque: bool
    mensagem: str


class ItemCarrinho(BaseModel):
    """Linha do carrinho ou de um pedido."""

    produto_id: int
    nome: str
    tamanho: Tamanho
    quantidade: int
    preco_unitario: float
    subtotal: float
    subtotal_formatado: str


class Carrinho(BaseModel):
    """Conteúdo do carrinho de uma sessão."""

    session_id: str
    itens: list[ItemCarrinho]
    quantidade_itens: int = Field(description="Total de unidades no carrinho.")
    total: float
    total_formatado: str


class OperacaoCarrinho(BaseModel):
    """Resultado de uma alteração no carrinho."""

    mensagem: str
    carrinho: Carrinho


class Pedido(BaseModel):
    """Pedido finalizado."""

    id: int
    session_id: str
    itens: list[ItemCarrinho]
    quantidade_itens: int
    total: float
    total_formatado: str
    endereco_entrega: str
    criado_em: str = Field(description="Data/hora de criação em ISO 8601 (UTC).")
    status: str
