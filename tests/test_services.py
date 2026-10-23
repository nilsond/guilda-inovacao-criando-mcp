import threading
from decimal import Decimal

import pytest

from vestuario_mcp.models import Categoria, Tamanho, formatar_brl
from vestuario_mcp.services import (
    CarrinhoVazio,
    CategoriaInvalida,
    EnderecoInvalido,
    EstoqueInsuficiente,
    ItemNaoEncontradoNoCarrinho,
    Loja,
    ProdutoNaoEncontrado,
    QuantidadeInvalida,
    SessaoInvalida,
    TamanhoInvalido,
)

ENDERECO = "Rua das Flores, 123 - Centro, São Paulo/SP - 01000-000"


def test_formatar_brl() -> None:
    assert formatar_brl(Decimal("1299.9")) == "R$ 1.299,90"
    assert formatar_brl(Decimal("79.90")) == "R$ 79,90"


# ---------------------------------------------------------------- catálogo


def test_catalogo_tem_pelo_menos_8_produtos_em_todas_as_categorias(loja: Loja) -> None:
    lista = loja.listar_produtos()
    assert lista.total >= 8
    assert {p.categoria for p in lista.produtos} == set(Categoria)


@pytest.mark.parametrize("entrada", ["Calças", "calcas", "  CALÇAS "])
def test_filtro_categoria_ignora_caixa_e_acento(loja: Loja, entrada: str) -> None:
    lista = loja.listar_produtos(entrada)
    assert lista.categoria_filtro == Categoria.CALCAS
    assert lista.total > 0
    assert all(p.categoria == Categoria.CALCAS for p in lista.produtos)


def test_categoria_invalida_lista_opcoes(loja: Loja) -> None:
    with pytest.raises(CategoriaInvalida, match="Camisetas"):
        loja.listar_produtos("Pijamas")


def test_produto_inexistente(loja: Loja) -> None:
    with pytest.raises(ProdutoNaoEncontrado, match="999"):
        loja.buscar_produto(999)


def test_tamanho_fora_da_grade_e_nao_vendido(loja: Loja) -> None:
    with pytest.raises(TamanhoInvalido, match="grade"):
        loja.verificar_estoque(1, "XG")
    with pytest.raises(TamanhoInvalido, match="não é vendido"):
        loja.verificar_estoque(5, "GG")  # Calça Chino: só P, M, G


def test_verificar_estoque_normaliza_tamanho_e_detecta_esgotado(loja: Loja) -> None:
    status = loja.verificar_estoque(1, " m ")
    assert status.tamanho == Tamanho.M
    assert status.disponivel == status.estoque_fisico == 20
    assert status.em_estoque

    esgotado = loja.verificar_estoque(3, "GG")  # Polo GG com estoque 0
    assert not esgotado.em_estoque
    assert "esgotado" in esgotado.mensagem


# ---------------------------------------------------------------- carrinho


def test_adicionar_reserva_estoque_e_agrupa_itens(loja: Loja) -> None:
    loja.adicionar_ao_carrinho("demo", 1, 2, "M")
    op = loja.adicionar_ao_carrinho("demo", 1, 3, "m")
    assert len(op.carrinho.itens) == 1
    assert op.carrinho.itens[0].quantidade == 5
    assert op.carrinho.total == pytest.approx(5 * 79.90)

    status = loja.verificar_estoque(1, "M")
    assert status.estoque_fisico == 20
    assert status.reservado == 5
    assert status.disponivel == 15


def test_reserva_afeta_outras_sessoes(loja: Loja) -> None:
    loja.adicionar_ao_carrinho("ana", 2, 1, "GG")  # única unidade
    with pytest.raises(EstoqueInsuficiente, match="0 unidade"):
        loja.adicionar_ao_carrinho("bruno", 2, 1, "GG")


@pytest.mark.parametrize("quantidade", [0, -1])
def test_quantidade_invalida(loja: Loja, quantidade: int) -> None:
    with pytest.raises(QuantidadeInvalida):
        loja.adicionar_ao_carrinho("demo", 1, quantidade, "M")


def test_estoque_insuficiente_informa_disponivel(loja: Loja) -> None:
    with pytest.raises(EstoqueInsuficiente, match="só há 2"):
        loja.adicionar_ao_carrinho("demo", 11, 3, "M")  # Bota M: 2 unidades


def test_session_id_vazio(loja: Loja) -> None:
    with pytest.raises(SessaoInvalida):
        loja.ver_carrinho("   ")


def test_remover_parcial_e_total_devolve_reserva(loja: Loja) -> None:
    loja.adicionar_ao_carrinho("demo", 7, 4, "G")
    op = loja.remover_do_carrinho("demo", 7, "G", 1)
    assert op.carrinho.itens[0].quantidade == 3
    assert loja.verificar_estoque(7, "G").reservado == 3

    op = loja.remover_do_carrinho("demo", 7, "G")
    assert op.carrinho.itens == []
    assert loja.verificar_estoque(7, "G").reservado == 0
    assert loja.verificar_estoque(7, "G").disponivel == 8


def test_remover_erros(loja: Loja) -> None:
    with pytest.raises(ItemNaoEncontradoNoCarrinho):
        loja.remover_do_carrinho("demo", 1, "M")
    loja.adicionar_ao_carrinho("demo", 1, 2, "M")
    with pytest.raises(QuantidadeInvalida, match="só 2"):
        loja.remover_do_carrinho("demo", 1, "M", 5)
    with pytest.raises(QuantidadeInvalida):
        loja.remover_do_carrinho("demo", 1, "M", 0)


def test_ver_carrinho_vazio(loja: Loja) -> None:
    carrinho = loja.ver_carrinho("novo")
    assert carrinho.itens == []
    assert carrinho.total == 0
    assert carrinho.total_formatado == "R$ 0,00"


def test_concorrencia_pela_ultima_unidade(loja: Loja) -> None:
    sucessos: list[str] = []
    falhas: list[str] = []
    barreira = threading.Barrier(20)

    def tentar(n: int) -> None:
        barreira.wait()
        try:
            loja.adicionar_ao_carrinho(f"cliente-{n}", 11, 1, "GG")  # Bota GG: 1 unidade
            sucessos.append(f"cliente-{n}")
        except EstoqueInsuficiente:
            falhas.append(f"cliente-{n}")

    threads = [threading.Thread(target=tentar, args=(n,)) for n in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(sucessos) == 1
    assert len(falhas) == 19
    status = loja.verificar_estoque(11, "GG")
    assert status.reservado == 1
    assert status.disponivel == 0


# ---------------------------------------------------------------- pedidos


def test_finalizar_pedido_baixa_estoque_e_limpa_carrinho(loja: Loja) -> None:
    loja.adicionar_ao_carrinho("demo", 4, 2, "M")
    loja.adicionar_ao_carrinho("demo", 10, 1, "G")
    pedido = loja.finalizar_pedido("demo", ENDERECO)

    assert pedido.status == "confirmado"
    assert pedido.quantidade_itens == 3
    assert pedido.total == pytest.approx(2 * 199.90 + 349.90)
    assert pedido.total_formatado == "R$ 749,70"

    jeans = loja.verificar_estoque(4, "M")
    assert (jeans.estoque_fisico, jeans.reservado, jeans.disponivel) == (12, 0, 12)
    tenis = loja.verificar_estoque(10, "G")
    assert (tenis.estoque_fisico, tenis.reservado) == (4, 0)

    assert loja.ver_carrinho("demo").itens == []
    assert loja.listar_pedidos("demo") == [pedido]


def test_pedidos_tem_ids_diferentes(loja: Loja) -> None:
    loja.adicionar_ao_carrinho("a", 1, 1, "P")
    p1 = loja.finalizar_pedido("a", ENDERECO)
    loja.adicionar_ao_carrinho("a", 1, 1, "P")
    p2 = loja.finalizar_pedido("a", ENDERECO)
    assert p1.id != p2.id


def test_finalizar_carrinho_vazio(loja: Loja) -> None:
    with pytest.raises(CarrinhoVazio):
        loja.finalizar_pedido("demo", ENDERECO)


@pytest.mark.parametrize("endereco", ["", "   ", "Rua A"])
def test_finalizar_endereco_invalido_nao_altera_nada(loja: Loja, endereco: str) -> None:
    loja.adicionar_ao_carrinho("demo", 1, 1, "M")
    with pytest.raises(EnderecoInvalido):
        loja.finalizar_pedido("demo", endereco)
    assert loja.ver_carrinho("demo").quantidade_itens == 1
    assert loja.verificar_estoque(1, "M").estoque_fisico == 20
