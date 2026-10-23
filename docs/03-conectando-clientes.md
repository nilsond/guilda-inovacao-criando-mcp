# Guia 3: Conectando clientes (MCP Inspector e Kiro)

Pré-requisito: projeto instalado (`.venv` criado e `pip install -e . --group dev` executado; veja o [Guia 1](01-criando-o-servidor.md)). Todos os comandos rodam na pasta do projeto.

Há três formas de conectar:

| Cenário | Transporte | Quem inicia o servidor | Quando usar |
|---|---|---|---|
| A. Local | STDIO | O próprio cliente | Uso local, o caso mais simples |
| B. HTTP local | Streamable HTTP | Você, no terminal | Servidor como "serviço", compartilhado por vários clientes na mesma máquina |
| C. Remoto | Streamable HTTP + ngrok | Você, no terminal | Acesso pela internet, a partir de outra máquina |

> 💡 **Estado compartilhado:** em STDIO, cada cliente sobe o **próprio** processo, com estoque e carrinhos separados. Em HTTP, todos os clientes falam com o **mesmo** processo. Assim, um item adicionado pelo Kiro aparece no `ver_carrinho` feito pelo Inspector.

---

# Parte 1: MCP Inspector

O [MCP Inspector](https://github.com/modelcontextprotocol/inspector) é a ferramenta visual oficial para testar servidores MCP. Ele roda via `npx` (precisa de Node.js 18+) e abre no navegador.

## 1.1 Cenário A: STDIO

```bash
npx @modelcontextprotocol/inspector .venv/bin/python server_mcp.py
```

O terminal mostra uma URL como `http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...` e normalmente abre o navegador sozinho. Na barra lateral, o comando já vem preenchido (Transport Type **STDIO**). Clique em **Connect**.

> Com o uv instalado, o atalho equivalente é `uv run mcp dev server_mcp.py`. O `mcp dev` do SDK depende do uv; sem ele, use o `npx` acima.

## 1.2 Cenário B: HTTP local

```bash
# Terminal 1
.venv/bin/python server_mcp.py --transport http

# Terminal 2
npx @modelcontextprotocol/inspector
```

Na barra lateral do Inspector:

- **Transport Type:** Streamable HTTP
- **URL:** `http://127.0.0.1:8000/mcp`
- **Connect**

## 1.3 Cenário C: remoto via ngrok

Com o túnel e o servidor rodando (veja o [Guia 2](02-expondo-com-ngrok.md)), repita o cenário B trocando a URL por `https://abc123.ngrok-free.app/mcp`.

## 1.4 Testando no Inspector

Os valores esperados abaixo partem do estoque inicial, com o servidor recém-iniciado.

**Aba Tools → List Tools.** Aparecem as 7 tools. Clique em uma para ver a descrição (a docstring) e o formulário gerado a partir dos type hints.

| # | Tool | Entrada | Resultado esperado |
|---|---|---|---|
| 1 | `listar_produtos` | `categoria`: `casacos` | `total: 2`. O filtro aceita minúsculas e sem acento. A resposta vem como JSON estruturado |
| 2 | `buscar_produto_por_id` | `produto_id`: `6` | Detalhes da Jaqueta Jeans e `disponivel_por_tamanho` |
| 3 | `verificar_estoque` | `6`, `M` | `estoque_fisico: 6`, `reservado: 0`, `disponivel: 6` |
| 4 | `adicionar_ao_carrinho` | `cliente-1`, `6`, `2`, `m` | Carrinho com 2 jaquetas, total `R$ 579,80` |
| 5 | `verificar_estoque` | `6`, `M` | Agora `reservado: 2`, `disponivel: 4`: **a reserva** |
| 6 | `adicionar_ao_carrinho` | `cliente-1`, `6`, `99`, `M` | **Erro** (`is_error`): "...só há 4 unidade(s) disponível(is)" |
| 7 | `verificar_estoque` | `3`, `GG` | Polo esgotada: `em_estoque: false` |
| 8 | `verificar_estoque` | `5`, `GG` | **Erro**: Calça Chino não é vendida em GG |
| 9 | `remover_do_carrinho` | `cliente-1`, `6`, `M`, `1` | 1 unidade sai e a reserva volta |
| 10 | `ver_carrinho` | `cliente-1` | 1 jaqueta, `R$ 289,90` |
| 11 | `finalizar_pedido` | `cliente-1`, `Av. Paulista, 1000 - Bela Vista, São Paulo/SP` | Pedido `1001`, `status: confirmado` |
| 12 | `verificar_estoque` | `6`, `M` | `estoque_fisico: 5`, `reservado: 0`: o pedido baixou o físico |
| 13 | `finalizar_pedido` | `cliente-1`, mesmo endereço | **Erro**: carrinho vazio |

> **Nota sobre os erros:** o Inspector mostra o resultado como erro, mas a conexão continua de pé. É um `ToolError` (`is_error: true`), não uma falha de protocolo. Um LLM lê essa mensagem e se corrige.

**Aba Resources → List Resources** → `politica-trocas`. Clique para ver o Markdown da política de trocas.

**Aba Prompts → List Prompts** → `recomendar_look`. Preencha `ocasiao` = `casamento de dia` e `estilo` = `clássico`, e clique em **Get Prompt**. A mensagem gerada traz as regras e o catálogo real embutido. É isso que o cliente entrega ao LLM.

> **Dica:** a área de histórico mostra o JSON-RPC de cada chamada. Abra uma para ver que, por baixo, é só `{"method": "tools/call", "params": {...}}`.

---

# Parte 2: Kiro

O Kiro funciona como cliente MCP: o agente lê a descrição das tools e decide sozinho quando chamar cada uma.

## 2.1 Cenário A: STDIO (local)

Crie o arquivo `.kiro/settings/mcp.json` **no workspace** do projeto. A configuração fica restrita a este projeto e não altera a global em `~/.kiro/settings/mcp.json`. Troque `/caminho/para/guilda-inovacao-criando-mcp` pelo caminho absoluto do seu clone.

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

| Campo | Para que serve |
|---|---|
| `command` / `args` | Como o Kiro inicia o servidor. Use caminhos absolutos para não depender do diretório atual |
| `disabled` | Liga e desliga o servidor sem apagar a entrada |
| `autoApprove` | Tools que rodam sem pedir confirmação. Vazio = o Kiro pede aprovação em cada chamada |

Com uv, a entrada pode ser:

```json
"vestuario-mcp": {
  "command": "uv",
  "args": ["--directory", "/caminho/para/guilda-inovacao-criando-mcp", "run", "server_mcp.py"]
}
```

O Kiro reconecta sozinho quando o arquivo muda. Confira em **Kiro → MCP Servers** (painel lateral do Kiro): `vestuario-mcp` deve aparecer conectado, com as 7 tools listadas. Se não aparecer, use a opção de reconectar nesse painel ou procure por "MCP" na paleta de comandos (`Cmd+Shift+P`).

## 2.2 Cenário C: remoto (ngrok)

O Kiro aceita servidores remotos pelo campo `url` ([documentação](https://kiro.dev/docs/mcp/configuration/)). Com o túnel e o servidor HTTP no ar, adicione uma segunda entrada:

```json
{
  "mcpServers": {
    "vestuario-mcp": { "...": "entrada STDIO acima" },
    "vestuario-mcp-remoto": {
      "url": "https://abc123.ngrok-free.app/mcp",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

> Deixe **só uma** das duas entradas ativa (`"disabled": true` na outra). Com as duas ativas, o agente vê as tools duplicadas e pode escolher qualquer uma.

Se a conexão pelo `url` falhar, use a ponte `mcp-remote`, que converte HTTP para STDIO:

```json
"vestuario-mcp-remoto": {
  "command": "npx",
  "args": ["-y", "mcp-remote", "https://abc123.ngrok-free.app/mcp"]
}
```

Ao usar o servidor remoto, o painel do ngrok (<http://127.0.0.1:4040>) ajuda a acompanhar o tráfego: cada tool que o Kiro chama aparece lá como uma requisição.

## 2.3 Exemplos de uso no Kiro

Use um `session_id` fixo (por exemplo, `cliente-1`) para o carrinho ser o mesmo em todas as mensagens.

1. **Descoberta:** "Quais casacos a Vestuário MCP tem e quanto custam?"
   → o agente chama `listar_produtos` com `categoria: "Casacos"`.
2. **Recomendação:** "Monte um look casual para um happy hour, com peças da loja."
   → `listar_produtos` e/ou `buscar_produto_por_id`; a resposta cita IDs reais.
3. **Estoque:** "Tem a jaqueta jeans no tamanho M?"
   → `verificar_estoque`.
4. **Carrinho:** "Adicione a jaqueta M e a camiseta básica M preta ao carrinho da sessão cliente-1."
   → duas chamadas a `adicionar_ao_carrinho`. **O Kiro pede aprovação** a cada uma (é o `autoApprove` vazio trabalhando).
5. **Erro e autocorreção:** "Adicione 3 botas chelsea tamanho M."
   → o servidor responde que só há 2; o agente explica e oferece 2 unidades.
6. **Política:** "Se não servir, consigo trocar? Qual é o prazo?"
   → o agente consulta a política de trocas (resource `ecommerce://politica-trocas`).
7. **Fechamento:** "Mostre o carrinho e finalize o pedido para Av. Paulista, 1000 - Bela Vista, São Paulo/SP."
   → `ver_carrinho` e depois `finalizar_pedido`.

> **Sobre resources e prompts no Kiro:** as tools são usadas automaticamente pelo agente. A forma de anexar resources e chamar prompts MCP pela interface pode variar com a versão do Kiro. Se não encontrar no chat, peça diretamente ("leia o resource ecommerce://politica-trocas") ou teste essas duas primitivas no Inspector.

## 2.4 Ajustando a aprovação automática

Por segurança, aprove automaticamente **apenas as tools de leitura**. As que alteram estado (`adicionar_ao_carrinho`, `remover_do_carrinho`, `finalizar_pedido`) devem continuar pedindo confirmação, para que você revise cada ação antes de o agente executá-la:

```json
"autoApprove": ["listar_produtos", "buscar_produto_por_id", "verificar_estoque", "ver_carrinho"]
```

Isso combina com as `ToolAnnotations` do servidor: essas quatro são marcadas com `read_only_hint=True`.

## 2.5 Problemas comuns no Kiro

| Sintoma | O que verificar |
|---|---|
| O servidor não conecta (STDIO) | Rode o comando do `mcp.json` no terminal: `/caminho/para/guilda-inovacao-criando-mcp/.venv/bin/python /caminho/para/guilda-inovacao-criando-mcp/server_mcp.py`. Ele deve ficar parado esperando (sem erro). Saia com `Ctrl+C` |
| `ModuleNotFoundError: vestuario_mcp` | Falta `pip install -e .` no `.venv` |
| As tools não aparecem | Reconecte no painel MCP e confira os logs de MCP no painel **Output** |
| O remoto falha | Teste com o `curl` do [Guia 2](02-expondo-com-ngrok.md#4-testar-o-endpoint-público). Se a URL do ngrok mudou, atualize o `url` |
| O estoque "volta ao normal" | O estado é em memória e reinicia quando o servidor reinicia. Em STDIO, o Kiro e o Inspector têm processos separados |

---

## Resumo dos comandos

```bash
# Inspector + STDIO
npx @modelcontextprotocol/inspector .venv/bin/python server_mcp.py

# Servidor HTTP local (Inspector/Kiro em http://127.0.0.1:8000/mcp)
.venv/bin/python server_mcp.py --transport http

# Servidor HTTP atrás do ngrok
ngrok http 8000
.venv/bin/python server_mcp.py --transport http --public-host abc123.ngrok-free.app
```
