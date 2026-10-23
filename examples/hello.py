# Importa a classe MCPServer do SDK oficial do MCP (v2).
# Ela é o antigo "FastMCP" da v1: cuida do protocolo, da validação e do transporte.
from mcp.server.mcpserver import MCPServer

# Cria o servidor. "Hello" é o nome que o cliente (Kiro, Inspector) vê no handshake (serverInfo.name).
mcp = MCPServer("Hello")

# O decorator registra a função abaixo como uma *tool* MCP. O nome da tool é o nome da função.
@mcp.tool()
# Os type hints viram o JSON Schema de entrada (a e b inteiros obrigatórios)
# e o "-> int" vira o schema de saída. Não é preciso escrever JSON Schema à mão.
def somar(a: int, b: int) -> int:
    # A docstring vira a descrição da tool: é o texto que o LLM lê para decidir quando chamá-la.
    """Soma dois números."""
    # A lógica da tool. O valor retornado é enviado ao cliente como resultado (texto e structured_content).
    return a + b

# Só executa o bloco abaixo quando o arquivo é rodado diretamente (python examples/hello.py), não quando é importado.
if __name__ == "__main__":
    # Inicia o servidor e bloqueia esperando mensagens. Sem argumentos, o transporte é STDIO:
    # o cliente fala por stdin/stdout, então não use print() aqui (isso corromperia o protocolo).
    mcp.run()
