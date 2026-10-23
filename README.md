# Vestuário MCP

![GitHub repo size](https://img.shields.io/github/repo-size/nilsond/guilda-inovacao-criando-mcp?style=for-the-badge)
![GitHub language count](https://img.shields.io/github/languages/count/nilsond/guilda-inovacao-criando-mcp?style=for-the-badge)
![GitHub forks](https://img.shields.io/github/forks/nilsond/guilda-inovacao-criando-mcp?style=for-the-badge)
![GitHub open issues](https://img.shields.io/github/issues/nilsond/guilda-inovacao-criando-mcp?style=for-the-badge)
![GitHub open pull requests](https://img.shields.io/github/issues-pr/nilsond/guilda-inovacao-criando-mcp?style=for-the-badge)

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MCP SDK 2.3.0](https://img.shields.io/badge/MCP%20SDK-2.3.0-6E56CF?style=for-the-badge)
[![License MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

> Servidor MCP em memória que simula o backend de um e-commerce de roupas: catálogo, carrinho com reserva de estoque e pedidos.
> Feito com o MCP Python SDK v2 (`mcp==2.3.0`), em que o antigo `FastMCP` agora se chama `MCPServer`.

> ⚠️ **Segurança:** o modo HTTP não tem autenticação. Qualquer pessoa com a URL do ngrok pode chamar as tools. Encerre o túnel ao terminar.

## 💻 Pré-requisitos

Antes de começar, verifique se você tem:

- Python `>= 3.11`.
- pip `>= 25.1` (necessário para a opção `--group`).
- Opcional: [Node.js](https://nodejs.org/) (para o MCP Inspector), [ngrok](https://ngrok.com/) e [uv](https://docs.astral.sh/uv/).

## 🚀 Instalando

Clone o repositório e entre na pasta:

```bash
git clone https://github.com/nilsond/guilda-inovacao-criando-mcp.git
cd guilda-inovacao-criando-mcp
```

Com **venv + pip** (é o que a configuração do Kiro abaixo usa):

```bash
python3 -m venv .venv && .venv/bin/pip install -e . --group dev
```

Ou, como alternativa, com **uv**:

```bash
uv sync
```

Com uv, troque `.venv/bin/python` por `uv run` nos comandos abaixo.

## ☕ Usando

O servidor expõe:

| Tipo | Nome | O que faz |
|---|---|---|
| Tool | `listar_produtos(categoria?)` | Lista o catálogo, com filtro opcional (Camisetas, Calças, Casacos, Acessórios, Calçados) |
| Tool | `buscar_produto_por_id(produto_id)` | Todos os detalhes de um produto |
| Tool | `verificar_estoque(produto_id, tamanho)` | Estoque físico, reservado e disponível |
| Tool | `adicionar_ao_carrinho(session_id, produto_id, quantidade, tamanho)` | Adiciona ao carrinho e **reserva** o estoque |
| Tool | `remover_do_carrinho(session_id, produto_id, tamanho, quantidade?)` | Remove o item e devolve a reserva |
| Tool | `ver_carrinho(session_id)` | Itens, subtotais e total em BRL |
| Tool | `finalizar_pedido(session_id, endereco_entrega)` | Cria o pedido, baixa o estoque e limpa o carrinho |
| Resource | `ecommerce://politica-trocas` | Política de trocas e devoluções (Markdown) |
| Prompt | `recomendar_look(ocasiao, estilo?)` | Consultor de estilo que monta looks com peças do catálogo |

Estoque por tamanho: `disponível = estoque físico − reservado`.

Erros de negócio (produto inexistente, tamanho inválido, estoque insuficiente etc.) voltam como resultado com `is_error=true` e uma mensagem em PT-BR, para o LLM conseguir se corrigir.

### MCP Inspector via STDIO

```bash
npx @modelcontextprotocol/inspector .venv/bin/python server_mcp.py   # com uv: uv run mcp dev server_mcp.py
```

O Inspector abre no navegador. Explore as abas Tools, Resources e Prompts. O `mcp dev` do SDK chama o `uv` por baixo, então sem uv use o `npx` direto.

### HTTP local

```bash
.venv/bin/python server_mcp.py --transport http           # http://127.0.0.1:8000/mcp
npx @modelcontextprotocol/inspector                       # em outro terminal
```

No Inspector, escolha **Streamable HTTP** e use a URL `http://127.0.0.1:8000/mcp`.

### Remoto via ngrok

```bash
ngrok http 8000                                            # anote o host, ex.: abc123.ngrok-free.app
.venv/bin/python server_mcp.py --transport http --public-host abc123.ngrok-free.app
```

No Inspector, conecte em `https://abc123.ngrok-free.app/mcp`.

O `--public-host` (ou a variável `PUBLIC_HOST`) é obrigatório nesse cenário. O SDK ativa uma proteção contra DNS rebinding que responde `421 Invalid Host header` para qualquer host fora da allowlist, e o ngrok repassa o host público.

### Kiro

**Local (STDIO):** crie o arquivo `.kiro/settings/mcp.json` no workspace com o conteúdo abaixo, trocando `/caminho/para/guilda-inovacao-criando-mcp` pelo caminho onde você clonou o repositório. O servidor aparece no painel MCP do Kiro; se precisar, reconecte por esse painel. `autoApprove` está vazio, então cada chamada de tool pede confirmação.

```json
{
  "mcpServers": {
    "vestuario-mcp": {
      "command": "/caminho/para/guilda-inovacao-criando-mcp/.venv/bin/python",
      "args": ["/caminho/para/guilda-inovacao-criando-mcp/server_mcp.py"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Com uv, a entrada fica assim:

```json
"vestuario-mcp": {
  "command": "uv",
  "args": ["--directory", "/caminho/para/guilda-inovacao-criando-mcp", "run", "server_mcp.py"]
}
```

**Remoto (ngrok):** o Kiro aceita servidores remotos pelo campo `url` ([documentação de configuração](https://kiro.dev/docs/mcp/configuration/), [anúncio de remote MCP](https://kiro.dev/blog/introducing-remote-mcp/)). Com o túnel e o servidor HTTP no ar, adicione:

```json
"vestuario-mcp-remoto": {
  "url": "https://abc123.ngrok-free.app/mcp"
}
```

Se o cliente não conectar, use a ponte `mcp-remote`:

```json
"vestuario-mcp-remoto": {
  "command": "npx",
  "args": ["-y", "mcp-remote", "https://abc123.ngrok-free.app/mcp"]
}
```

### Exemplos de uso

Com o servidor conectado ao Kiro (ou a outro cliente MCP), experimente:

1. "Quais casacos vocês têm e quanto custam?"
2. "Monte um look casual para um happy hour" (ou use o prompt `recomendar_look`)
3. "Adicione o look ao carrinho da sessão demo, tamanho M"
4. "Mostre o estoque da jaqueta no tamanho M" (a reserva aparece)
5. "Qual é a política de trocas?" (resource)
6. "Finalize o pedido para Av. Paulista, 1000 - Bela Vista, São Paulo/SP"

O estado vive na memória e é zerado sempre que o servidor reinicia.

### Exemplo mínimo

[examples/hello.py](examples/hello.py) é um servidor MCP com uma única tool (`somar`), comentado linha a linha. Bom ponto de partida para entender o `MCPServer` antes de olhar o projeto completo:

```bash
npx @modelcontextprotocol/inspector .venv/bin/python examples/hello.py
```

### Guias

- [docs/01-criando-o-servidor.md](docs/01-criando-o-servidor.md): criar o projeto do zero, passo a passo
- [docs/02-expondo-com-ngrok.md](docs/02-expondo-com-ngrok.md): expor o servidor com ngrok
- [docs/03-conectando-clientes.md](docs/03-conectando-clientes.md): usar o servidor no Kiro e no MCP Inspector

## 🧪 Testes

```bash
.venv/bin/python -m pytest        # ou: uv run pytest
.venv/bin/python -m pytest -q     # saída resumida
```

Os testes cobrem as regras de negócio (inclusive concorrência pela última unidade), as tools, o resource e o prompt via cliente MCP em memória, o servidor HTTP real com o bloqueio/liberação do host do ngrok, a CLI e o exemplo `examples/hello.py`.

## 📁 Estrutura do projeto

```
.
├── server_mcp.py              # CLI: --transport stdio|http, --host, --port, --public-host
├── src/vestuario_mcp/
│   ├── __init__.py            # exporta build_server e Loja
│   ├── models.py              # tipos e modelos Pydantic (viram structured output)
│   ├── data.py                # catálogo mock (11 produtos) e política de trocas
│   ├── services.py            # regras de negócio (classe Loja, com lock)
│   └── server.py              # build_server(): tools, resource e prompt
├── tests/                     # pytest: serviços, MCP em memória, CLI/HTTP e exemplos
├── examples/
│   └── hello.py               # servidor MCP mínimo
├── docs/
│   ├── 01-criando-o-servidor.md
│   ├── 02-expondo-com-ngrok.md
│   └── 03-conectando-clientes.md
├── pyproject.toml
├── LICENSE
└── README.md
```

## 📫 Contribuindo

Para contribuir com o projeto, siga estas etapas:

1. Bifurque este repositório.
2. Crie um branch: `git checkout -b <nome_branch>`.
3. Faça suas alterações e confirme-as: `git commit -m '<mensagem_commit>'`
4. Envie para o branch original: `git push origin <nome_branch>`
5. Crie a solicitação de pull.

Como alternativa, consulte a documentação do GitHub em [como criar uma solicitação pull](https://docs.github.com/pt/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request).

## 🤝 Colaboradores

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/nilsond" title="Nilson Damasio no GitHub">
        <img src="https://github.com/nilsond.png" width="100px;" alt="Foto de Nilson Damasio no GitHub"/><br>
        <sub>
          <b>Nilson Damasio</b>
        </sub>
      </a>
    </td>
  </tr>
</table>

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
