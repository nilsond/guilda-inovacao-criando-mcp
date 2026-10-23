"""Catálogo inicial (mock) do Vestuário MCP.

``catalogo_inicial()`` devolve objetos novos a cada chamada, para que cada instância
de ``Loja`` (e cada teste) comece com o estoque original.
"""

from __future__ import annotations

from decimal import Decimal

from vestuario_mcp.models import Categoria, Produto, Tamanho

P, M, G, GG = Tamanho.P, Tamanho.M, Tamanho.G, Tamanho.GG

POLITICA_TROCAS = """\
# Política de Trocas e Devoluções: Vestuário MCP

## Prazos
- **Arrependimento (compra online):** até **7 dias corridos** após o recebimento, conforme o art. 49 do Código de Defesa do Consumidor. Reembolso integral, inclusive do frete.
- **Troca por tamanho ou cor:** até **30 dias corridos** após o recebimento. A primeira troca tem frete grátis.
- **Defeito de fabricação:** até **90 dias** após o recebimento (art. 26 do CDC).

## Condições
- A peça deve estar sem sinais de uso, sem lavagem e sem odores, com a etiqueta original presa.
- Envie na embalagem original ou em outra que proteja o produto.
- Calçados devem voltar na caixa original, sem marcas de uso na sola.

## Itens que não podem ser trocados
- Peças íntimas, meias e itens de uso pessoal, por motivo de higiene (exceto em caso de defeito).
- Produtos personalizados ou feitos sob medida.
- Itens comprados em liquidação final, quando isso estiver indicado no anúncio (exceto em caso de defeito).

## Como solicitar
1. Informe o número do pedido e o motivo pelo canal de atendimento.
2. Você recebe um código de postagem reversa em até 1 dia útil.
3. Depois que a peça chega, analisamos em até 3 dias úteis.

## Reembolso
- **Cartão de crédito:** estorno em até 2 faturas.
- **Pix ou boleto:** depósito na conta do titular em até 5 dias úteis.
- Na troca você pode escolher um **vale-compras** no valor da peça, liberado na hora.
"""


def catalogo_inicial() -> dict[int, Produto]:
    """Cria o catálogo inicial com 11 produtos distribuídos nas 5 categorias."""
    produtos = [
        Produto(
            id=1,
            nome="Camiseta Básica Algodão Orgânico",
            categoria=Categoria.CAMISETAS,
            preco=Decimal("79.90"),
            tamanhos=[P, M, G, GG],
            cores=["Branco", "Preto", "Cinza Mescla"],
            estoque={P: 15, M: 20, G: 18, GG: 8},
            descricao="Camiseta de malha 100% algodão orgânico, gola careca e caimento regular. Peça coringa do guarda-roupa.",
        ),
        Produto(
            id=2,
            nome='Camiseta Estampada "Hello MCP"',
            categoria=Categoria.CAMISETAS,
            preco=Decimal("99.90"),
            tamanhos=[P, M, G, GG],
            cores=["Preto", "Azul Marinho"],
            estoque={P: 5, M: 10, G: 7, GG: 1},
            descricao="Camiseta com estampa em silk do protocolo MCP. Modelagem levemente oversized.",
        ),
        Produto(
            id=3,
            nome="Polo Piquet Clássica",
            categoria=Categoria.CAMISETAS,
            preco=Decimal("139.90"),
            tamanhos=[P, M, G, GG],
            cores=["Azul Marinho", "Verde Musgo", "Branco"],
            estoque={P: 6, M: 12, G: 9, GG: 0},
            descricao="Camisa polo em malha piquet com botões de madrepérola. Combina com o casual e com o esporte fino.",
        ),
        Produto(
            id=4,
            nome="Calça Jeans Slim",
            categoria=Categoria.CALCAS,
            preco=Decimal("199.90"),
            tamanhos=[P, M, G, GG],
            cores=["Azul Escuro", "Azul Claro"],
            estoque={P: 8, M: 14, G: 10, GG: 4},
            descricao="Jeans com 2% de elastano, modelagem slim e lavagem amaciada. Grade P=38, M=40/42, G=44, GG=46/48.",
        ),
        Produto(
            id=5,
            nome="Calça Chino Sarja",
            categoria=Categoria.CALCAS,
            preco=Decimal("179.90"),
            tamanhos=[P, M, G],
            cores=["Bege", "Caqui", "Preto"],
            estoque={P: 5, M: 9, G: 3},
            descricao="Calça chino de sarja leve, com bolso faca e barra italiana. Funciona no trabalho e no fim de semana.",
        ),
        Produto(
            id=6,
            nome="Jaqueta Jeans Oversized",
            categoria=Categoria.CASACOS,
            preco=Decimal("289.90"),
            tamanhos=[P, M, G, GG],
            cores=["Azul Médio"],
            estoque={P: 3, M: 6, G: 4, GG: 2},
            descricao="Jaqueta jeans de modelagem ampla, com botões metálicos e bolsos frontais. Boa para usar em camadas.",
        ),
        Produto(
            id=7,
            nome="Moletom Canguru Essential",
            categoria=Categoria.CASACOS,
            preco=Decimal("229.90"),
            tamanhos=[P, M, G, GG],
            cores=["Cinza", "Preto", "Off-White"],
            estoque={P: 7, M: 11, G: 8, GG: 5},
            descricao="Moletom flanelado com capuz e bolso canguru. Interior macio para os dias frios.",
        ),
        Produto(
            id=8,
            nome="Boné Aba Curva Bordado",
            categoria=Categoria.ACESSORIOS,
            preco=Decimal("69.90"),
            tamanhos=[M, G],
            cores=["Preto", "Bege"],
            estoque={M: 12, G: 6},
            descricao="Boné de sarja com logo bordado e regulagem traseira. M=56-58 cm, G=58-60 cm.",
        ),
        Produto(
            id=9,
            nome="Cinto de Couro Legítimo",
            categoria=Categoria.ACESSORIOS,
            preco=Decimal("119.90"),
            tamanhos=[P, M, G, GG],
            cores=["Marrom", "Preto"],
            estoque={P: 4, M: 8, G: 8, GG: 3},
            descricao="Cinto de couro bovino com fivela de metal escovado. P=85 cm, M=95 cm, G=105 cm, GG=115 cm.",
        ),
        Produto(
            id=10,
            nome="Tênis Casual Couro",
            categoria=Categoria.CALCADOS,
            preco=Decimal("349.90"),
            tamanhos=[P, M, G, GG],
            cores=["Branco", "Preto"],
            estoque={P: 4, M: 6, G: 5, GG: 2},
            descricao="Tênis minimalista de couro com solado de borracha costurado. P=34-36, M=37-39, G=40-42, GG=43-44.",
        ),
        Produto(
            id=11,
            nome="Bota Chelsea Camurça",
            categoria=Categoria.CALCADOS,
            preco=Decimal("429.90"),
            tamanhos=[M, G, GG],
            cores=["Caramelo", "Preto"],
            estoque={M: 2, G: 3, GG: 1},
            descricao="Bota chelsea de camurça com elástico lateral e solado tratorado. M=37-39, G=40-42, GG=43-44.",
        ),
    ]
    return {produto.id: produto for produto in produtos}
