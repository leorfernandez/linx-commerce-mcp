#!/usr/bin/env python3
"""
Linx Commerce MCP Server para Claude Code
Permite ler e editar arquivos do tema diretamente pelo Claude Code

Endpoints descobertos:
- GET  /CMS/FileManagement - Listar arquivos (iframe)
- POST /CMS/FileManagement/LoadFileContents - Ler arquivo
- POST /CMS/FileManagement/Edit - Salvar arquivo
- POST /CMS/FileManagement/UploadMultiple - Upload de arquivos
- GET  /Shell/FileSystemPicker/FileSelect - Picker de arquivos
- POST /Shell/Security/Logon - Login
"""

import asyncio
import json
import os
import sys
from typing import Optional
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# Configurações do Linx Commerce
BASE_URL = os.environ.get("LINX_BASE_URL", "https://kingstarcolchoes.admin.core-hlg.dcg.com.br")
USERNAME = os.environ.get("LINX_USERNAME", "")
PASSWORD = os.environ.get("LINX_PASSWORD", "")
THEME_PATH = os.environ.get("LINX_THEME_PATH", "/Custom/Content/Themes")

app = Server("linx-commerce")

# Cliente HTTP compartilhado (mantém cookies de sessão)
client: Optional[httpx.AsyncClient] = None
session_token: Optional[str] = None

async def get_client() -> httpx.AsyncClient:
    global client
    if client is None:
        client = httpx.AsyncClient(
            base_url=BASE_URL,
            follow_redirects=True,
            timeout=30.0
        )
    return client

async def login() -> bool:
    """Faz login no Linx Commerce e mantém a sessão"""
    global session_token
    c = await get_client()
    
    # 1. Pegar o token CSRF da página de login
    resp = await c.get("/Shell/Security/Logon")
    
    # Extrair o token de verificação
    import re
    token_match = re.search(r'name="__RequestVerificationToken"\s+value="([^"]+)"', resp.text)
    if not token_match:
        return False
    
    csrf_token = token_match.group(1)
    
    # 2. Fazer login
    login_resp = await c.post("/Shell/Security/Logon", data={
        "UserName": USERNAME,
        "Password": PASSWORD,
        "__RequestVerificationToken": csrf_token,
        "keepAlive": "false"
    })
    
    # 3. Pegar novo token CSRF após login
    cms_resp = await c.get(f"/CMS/FileManagement?FilePath={THEME_PATH}&EditorCustomPath={THEME_PATH}&hasFilter=true")
    token_match2 = re.search(r'name="__RequestVerificationToken"\s+value="([^"]+)"', cms_resp.text)
    if token_match2:
        session_token = token_match2.group(1)
    
    return session_token is not None

async def ensure_session() -> bool:
    """Garante que há uma sessão válida"""
    global session_token
    if not session_token:
        return await login()
    return True

async def list_files(path: str = None) -> dict:
    """Lista arquivos em um caminho do tema"""
    if not await ensure_session():
        return {"error": "Falha no login"}
    
    c = await get_client()
    file_path = path or THEME_PATH
    resp = await c.get(f"/CMS/FileManagement?FilePath={file_path}&EditorCustomPath={THEME_PATH}&hasFilter=true")
    
    # Extrair lista de arquivos do HTML (Telerik TreeView)
    import re
    items = re.findall(r'itemValue.*?value="([^"]+)"', resp.text)
    return {"files": items, "path": file_path}

async def read_file(file_path: str) -> str:
    """Lê o conteúdo de um arquivo do tema"""
    if not await ensure_session():
        return "Erro: Falha no login"
    
    c = await get_client()
    
    # Garantir que o path começa com /Custom/Content/Themes/
    if not file_path.startswith("/Custom/Content/Themes/"):
        file_path = f"/Custom/Content/Themes/{file_path.lstrip('/')}"
    
    resp = await c.post("/CMS/FileManagement/LoadFileContents", data={
        "__RequestVerificationToken": session_token,
        "FilePath": file_path,
        "EditorCustomPath": THEME_PATH
    })
    
    return resp.text

async def write_file(file_path: str, content: str) -> bool:
    """Salva o conteúdo de um arquivo do tema"""
    if not await ensure_session():
        return False
    
    c = await get_client()
    
    if not file_path.startswith("/Custom/Content/Themes/"):
        file_path = f"/Custom/Content/Themes/{file_path.lstrip('/')}"
    
    resp = await c.post("/CMS/FileManagement/Edit", data={
        "__RequestVerificationToken": session_token,
        "FilePath": file_path,
        "FileContent": content,
        "EditorCustomPath": THEME_PATH
    })
    
    return resp.status_code == 200

# Definir as ferramentas MCP
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="linx_list_files",
            description="Lista os arquivos e pastas do tema no Linx Commerce",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Caminho da pasta (ex: /Custom/Content/Themes/Kingstar/CSS)"
                    }
                }
            }
        ),
        types.Tool(
            name="linx_read_file",
            description="Lê o conteúdo de um arquivo do tema Linx Commerce",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Caminho do arquivo (ex: /Custom/Content/Themes/Kingstar/CSS/main.css)"
                    }
                },
                "required": ["file_path"]
            }
        ),
        types.Tool(
            name="linx_write_file",
            description="Salva/edita o conteúdo de um arquivo do tema Linx Commerce",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Caminho do arquivo"
                    },
                    "content": {
                        "type": "string",
                        "description": "Conteúdo do arquivo"
                    }
                },
                "required": ["file_path", "content"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "linx_list_files":
        result = await list_files(arguments.get("path"))
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    
    elif name == "linx_read_file":
        content = await read_file(arguments["file_path"])
        return [types.TextContent(type="text", text=content)]
    
    elif name == "linx_write_file":
        success = await write_file(arguments["file_path"], arguments["content"])
        return [types.TextContent(type="text", text="Arquivo salvo com sucesso!" if success else "Erro ao salvar arquivo")]
    
    return [types.TextContent(type="text", text=f"Ferramenta desconhecida: {name}")]

async def main():
    if not USERNAME or not PASSWORD:
        print("ERRO: Configure LINX_USERNAME e LINX_PASSWORD como variáveis de ambiente", file=sys.stderr)
        sys.exit(1)
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
