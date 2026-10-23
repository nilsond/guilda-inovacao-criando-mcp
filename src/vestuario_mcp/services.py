"""Regras de negócio do Vestuário MCP: catálogo, carrinho com reserva de estoque e pedidos.

Contabilidade do estoque, por produto e tamanho:

- ``estoque``: unidades físicas no depósito.
- ``reservado``: unidades que estão em carrinhos ainda não finalizados.
- ``disponível = estoque - reservado``: o que ainda pode entrar em um carrinho.

``adicionar_ao_carrinho`` aumenta ``reservado``, ``remover_do_carrinho`` diminui
``reservado`` e ``finalizar_pedido`` diminui ``estoque`` e ``reservado`` juntos.
As reservas não expiram.

No MCP SDK v2 os handlers síncronos rodam em worker threads, então toda leitura
e escrita do estado passa por um ``threading.RLock``.
"""

from __future__ import annotations

import threading
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal

from vestuario_mcp.data import catalogo_inicial
from vestuario_mcp.models import (
    Carrinho,
    Categoria,
    ItemCarrinho,
    ListaProdutos,
    OperacaoCarrinho,
    Pedido,
    Produto,
    ProdutoDetalhe,
    ProdutoResumo,
    StatusEstoque,
    Tamanho,
    formatar_brl,
    para_float,
)

# --------------------------------------------------------------------------- #
# Exceções de domínio (mensagens em PT-BR, pensadas para o LLM se corrigir)
# --------------------------------------------------------------------------- #


class ErroLoja(Exception):
    """Base de todos os erros de negócio da loja."""


class ProdutoNaoEncontrado(ErroLoja):
    """O ID informado não existe no catálogo."""


class CategoriaInvalida(ErroLoja):
    """A categoria informada não existe."""


class TamanhoInvalido(ErroLoja):
    """O tamanho não faz parte da grade P/M/G/GG ou o produto não é vendido nele."""


class QuantidadeInvalida(ErroLoja):
    """A quantidade deve ser um inteiro maior que zero."""


class EstoqueInsuficiente(ErroLoja):
    """Não há unidades disponíveis suficientes para reservar."""


class SessaoInvalida(ErroLoja):
    """O session_id está vazio."""


class ItemNaoEncontradoNoCarrinho(ErroLoja):
    """O produto/tamanho informado não está no carrinho."""


class CarrinhoVazio(ErroLoja):
    """Não é possível finalizar um pedido com o carrinho vazio."""


class EnderecoInvalido(ErroLoja):
    """O endereço de entrega está vazio ou é curto demais."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _sem_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c)).casefold().strip()


_CATEGORIAS_POR_CHAVE: dict[str, Categoria] = {_sem_acentos(c.value): c for c in Categoria}


def parse_categoria(categoria: str) -> Categoria:
    """Converte texto livre em ``Categoria``, sem diferenciar maiúsculas/minúsculas nem acentos."""
    encontrada = _CATEGORIAS_POR_CHAVE.get(_sem_acentos(categoria))
    if encontrada is None:
        validas = ", ".join(c.value for c in Categoria)
        raise CategoriaInvalida(f"Categoria '{categoria}' não existe. Categorias válidas: {validas}.")
    return encontrada


def parse_tamanho(tamanho: str) -> Tamanho:
    """Converte texto livre (ex.: ``" m "``) em ``Tamanho``."""
    try:
        return Tamanho(tamanho.strip().upper())
    except ValueError:
        validos = ", ".join(t.value for t in Tamanho)
        raise TamanhoInvalido(f"Tamanho '{tamanho}' inválido. A grade da loja é: {validos}.") from None


def _validar_session_id(session_id: str) -> str:
    sessao = session_id.strip()
    if not sessao:
        raise SessaoInvalida("Informe um session_id não vazio para identificar o carrinho do cliente.")
    return sessao


# --------------------------------------------------------------------------- #
# Loja
# --------------------------------------------------------------------------- #


class Loja:
    """Estado em memória da loja e suas operações.

    Cada instância tem catálogo, carrinhos e pedidos próprios, o que deixa os testes isolados.
    """

    def __init__(self, produtos: dict[int, Produto] | None = None) -> None:
        self._lock = threading.RLock()
        self._produtos: dict[int, Produto] = produtos if produtos is not None else catalogo_inicial()
        # session_id -> {(produto_id, tamanho): quantidade}; dict preserva a ordem de inserção.
        self._carrinhos: dict[str, dict[tuple[int, Tamanho], int]] = {}
        self._pedidos: list[Pedido] = []
        self._proximo_pedido_id = 1001

    # ------------------------------------------------------------------ catálogo

    def _produto(self, produto_id: int) -> Produto:
        produto = self._produtos.get(produto_id)
        if produto is None:
            ids = ", ".join(str(i) for i in sorted(self._produtos))
            raise ProdutoNaoEncontrado(
                f"Produto com ID {produto_id} não encontrado. IDs existentes: {ids}. "
                "Use listar_produtos para consultar o catálogo."
            )
        return produto

    @staticmethod
    def _tamanho_do_produto(produto: Produto, tamanho: str) -> Tamanho:
        tam = parse_tamanho(tamanho)
        if tam not in produto.tamanhos:
            oferecidos = ", ".join(t.value for t in produto.tamanhos)
            raise TamanhoInvalido(
                f"O produto '{produto.nome}' (ID {produto.id}) não é vendido no tamanho {tam.value}. "
                f"Tamanhos disponíveis: {oferecidos}."
            )
        return tam

    @staticmethod
    def _resumo(produto: Produto) -> ProdutoResumo:
        return ProdutoResumo(
            id=produto.id,
            nome=produto.nome,
            categoria=produto.categoria,
            preco=para_float(produto.preco),
            preco_formatado=formatar_brl(produto.preco),
            tamanhos=list(produto.tamanhos),
            cores=list(produto.cores),
            disponivel_total=sum(produto.disponivel(t) for t in produto.tamanhos),
        )

    def listar_produtos(self, categoria: str | None = None) -> ListaProdutos:
        """Lista o catálogo, com filtro opcional por categoria."""
        filtro = parse_categoria(categoria) if categoria and categoria.strip() else None
        with self._lock:
            produtos = [
                self._resumo(p)
                for p in self._produtos.values()
                if filtro is None or p.categoria == filtro
            ]
        return ListaProdutos(categoria_filtro=filtro, total=len(produtos), produtos=produtos)

    def buscar_produto(self, produto_id: int) -> ProdutoDetalhe:
        """Devolve todos os detalhes de um produto."""
        with self._lock:
            produto = self._produto(produto_id)
            return ProdutoDetalhe(
                **self._resumo(produto).model_dump(),
                descricao=produto.descricao,
                disponivel_por_tamanho={t: produto.disponivel(t) for t in produto.tamanhos},
            )

    def verificar_estoque(self, produto_id: int, tamanho: str) -> StatusEstoque:
        """Consulta estoque físico, reservas e disponibilidade de um produto/tamanho."""
        with self._lock:
            produto = self._produto(produto_id)
            tam = self._tamanho_do_produto(produto, tamanho)
            fisico = produto.estoque.get(tam, 0)
            reservado = produto.reservado.get(tam, 0)
            disponivel = fisico - reservado
        if disponivel > 0:
            mensagem = f"Há {disponivel} unidade(s) de '{produto.nome}' disponível(is) no tamanho {tam.value}."
        elif fisico > 0:
            mensagem = (
                f"Todas as {fisico} unidade(s) de '{produto.nome}' no tamanho {tam.value} "
                "estão reservadas em carrinhos."
            )
        else:
            mensagem = f"'{produto.nome}' está esgotado no tamanho {tam.value}."
        return StatusEstoque(
            produto_id=produto.id,
            nome=produto.nome,
            tamanho=tam,
            estoque_fisico=fisico,
            reservado=reservado,
            disponivel=disponivel,
            em_estoque=disponivel > 0,
            mensagem=mensagem,
        )

    # ------------------------------------------------------------------ carrinho

    def _montar_itens(self, linhas: dict[tuple[int, Tamanho], int]) -> tuple[list[ItemCarrinho], Decimal, int]:
        itens: list[ItemCarrinho] = []
        total = Decimal("0")
        unidades = 0
        for (produto_id, tam), quantidade in linhas.items():
            produto = self._produtos[produto_id]
            subtotal = produto.preco * quantidade
            total += subtotal
            unidades += quantidade
            itens.append(
                ItemCarrinho(
                    produto_id=produto_id,
                    nome=produto.nome,
                    tamanho=tam,
                    quantidade=quantidade,
                    preco_unitario=para_float(produto.preco),
                    subtotal=para_float(subtotal),
                    subtotal_formatado=formatar_brl(subtotal),
                )
            )
        return itens, total, unidades

    def _carrinho(self, session_id: str) -> Carrinho:
        itens, total, unidades = self._montar_itens(self._carrinhos.get(session_id, {}))
        return Carrinho(
            session_id=session_id,
            itens=itens,
            quantidade_itens=unidades,
            total=para_float(total),
            total_formatado=formatar_brl(total),
        )

    def adicionar_ao_carrinho(
        self, session_id: str, produto_id: int, quantidade: int, tamanho: str
    ) -> OperacaoCarrinho:
        """Reserva ``quantidade`` unidades e as adiciona ao carrinho da sessão."""
        sessao = _validar_session_id(session_id)
        if quantidade <= 0:
            raise QuantidadeInvalida(f"Quantidade inválida ({quantidade}). Informe um inteiro maior que zero.")
        with self._lock:
            produto = self._produto(produto_id)
            tam = self._tamanho_do_produto(produto, tamanho)
            disponivel = produto.disponivel(tam)
            if quantidade > disponivel:
                raise EstoqueInsuficiente(
                    f"Estoque insuficiente para '{produto.nome}' no tamanho {tam.value}: "
                    f"você pediu {quantidade}, mas só há {disponivel} unidade(s) disponível(is)."
                )
            produto.reservado[tam] = produto.reservado.get(tam, 0) + quantidade
            linhas = self._carrinhos.setdefault(sessao, {})
            linhas[(produto.id, tam)] = linhas.get((produto.id, tam), 0) + quantidade
            return OperacaoCarrinho(
                mensagem=(
                    f"{quantidade}x '{produto.nome}' (tamanho {tam.value}) adicionado(s) e reservado(s) "
                    f"no carrinho '{sessao}'."
                ),
                carrinho=self._carrinho(sessao),
            )

    def remover_do_carrinho(
        self, session_id: str, produto_id: int, tamanho: str, quantidade: int | None = None
    ) -> OperacaoCarrinho:
        """Remove um item (inteiro ou parcialmente) do carrinho e devolve a reserva ao estoque."""
        sessao = _validar_session_id(session_id)
        if quantidade is not None and quantidade <= 0:
            raise QuantidadeInvalida(
                f"Quantidade inválida ({quantidade}). Informe um inteiro maior que zero "
                "ou omita o campo para remover o item inteiro."
            )
        with self._lock:
            produto = self._produto(produto_id)
            tam = parse_tamanho(tamanho)
            linhas = self._carrinhos.get(sessao, {})
            chave = (produto.id, tam)
            no_carrinho = linhas.get(chave, 0)
            if no_carrinho == 0:
                raise ItemNaoEncontradoNoCarrinho(
                    f"'{produto.nome}' no tamanho {tam.value} não está no carrinho '{sessao}'. "
                    "Use ver_carrinho para conferir os itens."
                )
            remover = no_carrinho if quantidade is None else quantidade
            if remover > no_carrinho:
                raise QuantidadeInvalida(
                    f"O carrinho tem só {no_carrinho} unidade(s) de '{produto.nome}' no tamanho {tam.value}; "
                    f"não dá para remover {remover}."
                )
            produto.reservado[tam] -= remover
            if remover == no_carrinho:
                del linhas[chave]
            else:
                linhas[chave] = no_carrinho - remover
            if not linhas:
                self._carrinhos.pop(sessao, None)
            return OperacaoCarrinho(
                mensagem=(
                    f"{remover}x '{produto.nome}' (tamanho {tam.value}) removido(s) do carrinho '{sessao}'. "
                    "A reserva voltou para o estoque."
                ),
                carrinho=self._carrinho(sessao),
            )

    def ver_carrinho(self, session_id: str) -> Carrinho:
        """Mostra o carrinho da sessão. Uma sessão sem itens devolve carrinho vazio."""
        sessao = _validar_session_id(session_id)
        with self._lock:
            return self._carrinho(sessao)

    # ------------------------------------------------------------------ pedidos

    def finalizar_pedido(self, session_id: str, endereco_entrega: str) -> Pedido:
        """Converte o carrinho em pedido, baixa o estoque físico e limpa o carrinho."""
        sessao = _validar_session_id(session_id)
        endereco = " ".join(endereco_entrega.split())
        if len(endereco) < 10:
            raise EnderecoInvalido(
                "Informe um endereço de entrega completo (rua, número, bairro, cidade/UF e CEP)."
            )
        with self._lock:
            linhas = self._carrinhos.get(sessao)
            if not linhas:
                raise CarrinhoVazio(
                    f"O carrinho '{sessao}' está vazio. Adicione itens com adicionar_ao_carrinho antes de finalizar."
                )
            # Confere a invariante antes de mexer em qualquer coisa: a operação é tudo ou nada.
            for (produto_id, tam), quantidade in linhas.items():
                produto = self._produtos[produto_id]
                if produto.reservado.get(tam, 0) < quantidade or produto.estoque.get(tam, 0) < quantidade:
                    raise EstoqueInsuficiente(
                        f"Inconsistência de estoque em '{produto.nome}' (tamanho {tam.value}). Pedido não finalizado."
                    )
            itens, total, unidades = self._montar_itens(linhas)
            for (produto_id, tam), quantidade in linhas.items():
                produto = self._produtos[produto_id]
                produto.estoque[tam] -= quantidade
                produto.reservado[tam] -= quantidade
            pedido = Pedido(
                id=self._proximo_pedido_id,
                session_id=sessao,
                itens=itens,
                quantidade_itens=unidades,
                total=para_float(total),
                total_formatado=formatar_brl(total),
                endereco_entrega=endereco,
                criado_em=datetime.now(UTC).isoformat(timespec="seconds"),
                status="confirmado",
            )
            self._proximo_pedido_id += 1
            self._pedidos.append(pedido)
            del self._carrinhos[sessao]
            return pedido

    def listar_pedidos(self, session_id: str | None = None) -> list[Pedido]:
        """Histórico de pedidos, com filtro opcional por sessão."""
        with self._lock:
            return [p for p in self._pedidos if session_id is None or p.session_id == session_id]

    def resumo_catalogo(self) -> str:
        """Texto compacto do catálogo, usado no prompt de estilo."""
        with self._lock:
            linhas = [
                f"- ID {p.id} | {p.nome} | {p.categoria.value} | cores: {', '.join(p.cores)} | "
                f"tamanhos: {', '.join(t.value for t in p.tamanhos)} | {formatar_brl(p.preco)}"
                for p in self._produtos.values()
            ]
        return "\n".join(linhas)
