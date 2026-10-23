"""Ponto de entrada do servidor MCP "Vestuário MCP".

Exemplos:
    python server_mcp.py                                   # STDIO (Kiro, Inspector local)
    python server_mcp.py --transport http                  # Streamable HTTP em http://127.0.0.1:8000/mcp
    python server_mcp.py --transport http --public-host abc123.ngrok-free.app   # atrás do ngrok
    mcp dev server_mcp.py                                  # MCP Inspector (usa a variável `mcp` abaixo)

ATENÇÃO: o modo HTTP não tem autenticação. Use apenas para demonstração.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence

from mcp.server.transport_security import TransportSecuritySettings

from vestuario_mcp import build_server

logger = logging.getLogger("vestuario_mcp")

# Instância no nível do módulo: `mcp dev server_mcp.py` / `mcp run server_mcp.py` procuram por ela.
mcp = build_server()


def normalizar_host_publico(valor: str | None) -> str | None:
    """Aceita 'abc.ngrok-free.app', 'https://abc.ngrok-free.app/' ou '.../mcp' e devolve só o host."""
    if not valor or not valor.strip():
        return None
    host = valor.strip()
    for prefixo in ("https://", "http://"):
        if host.lower().startswith(prefixo):
            host = host[len(prefixo):]
    return host.split("/", 1)[0] or None


def montar_transport_security(public_host: str | None) -> TransportSecuritySettings:
    """Monta a allowlist da proteção contra DNS rebinding.

    O SDK rejeita com ``421 Invalid Host header`` qualquer Host fora da lista. O ngrok repassa
    o Host público (ex.: ``abc123.ngrok-free.app``), então ele precisa estar na lista.
    """
    allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    allowed_origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    host = normalizar_host_publico(public_host)
    if host:
        allowed_hosts += [host, f"{host}:*"]
        allowed_origins += [f"https://{host}", f"http://{host}"]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Interpreta os argumentos de linha de comando."""
    parser = argparse.ArgumentParser(description="Servidor MCP da loja Vestuário MCP.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio (padrão, para Kiro/Inspector local) ou http (Streamable HTTP, para ngrok).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Interface HTTP (padrão: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Porta HTTP (padrão: 8000).")
    parser.add_argument(
        "--public-host",
        default=os.environ.get("PUBLIC_HOST"),
        help="Host público liberado na proteção de DNS rebinding, ex.: abc123.ngrok-free.app "
        "(padrão: variável de ambiente PUBLIC_HOST).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Sobe o servidor no transporte escolhido."""
    args = parse_args(argv)
    # Logs sempre no stderr: no modo STDIO o stdout é o canal do protocolo.
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")

    if args.transport == "stdio":
        logger.info("Vestuário MCP rodando em STDIO.")
        mcp.run(transport="stdio")
        return

    public_host = normalizar_host_publico(args.public_host)
    logger.warning(
        "ATENÇÃO: endpoint HTTP SEM AUTENTICAÇÃO. Qualquer pessoa com a URL pode chamar as tools. "
        "Use só para demonstração e encerre o túnel ao terminar."
    )
    logger.info("Endpoint local: http://%s:%s/mcp", args.host, args.port)
    if public_host:
        logger.info("Host público liberado: https://%s/mcp", public_host)
    mcp.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        transport_security=montar_transport_security(public_host),
    )


if __name__ == "__main__":
    main()
