# Linx Commerce MCP — Kingstar Colchões

Projeto de integração Claude Code ↔ Linx Commerce via MCP Server.

## Sobre

MCP Server em Python para interagir com o painel admin do Linx Commerce da Kingstar Colchões.

- **Ambiente**: Homologação (`kingstarcolchoes.admin.core-hlg.dcg.com.br`)
- **Usuário**: leonardofernandez@v4company.com

## Estrutura

```
linx-mcp/
└── server.py    # MCP Server principal
```

## Setup

```bash
# Instalar dependências
/opt/homebrew/opt/python@3.12/bin/python3.12 -m pip install --user --break-system-packages mcp httpx anyio

# O MCP já está configurado em ~/.claude/settings.local.json
```

## Como usar

Após reiniciar o Claude Code, o MCP `linx-commerce` estará disponível. Exemplos:

- "Liste os arquivos do tema Kingstar"
- "Leia o CSS principal do site"
- "Edite o template da página de produto"
