"""Autenticação simplificada da POC com app.storage.user e middleware (Seção 8.4)."""

from __future__ import annotations

from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.models import Usuario

UNRESTRICTED_PREFIXES = ("/_nicegui", "/assets", "/favicon")
UNRESTRICTED_EXACT = {"/login"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Redireciona para /login qualquer requisição de página sem sessão autenticada."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in UNRESTRICTED_EXACT or any(path.startswith(p) for p in UNRESTRICTED_PREFIXES):
            return await call_next(request)

        if not app.storage.user.get("authenticated", False):
            app.storage.user["referrer_path"] = path
            return RedirectResponse("/login")

        return await call_next(request)


def login_usuario(usuario: Usuario) -> None:
    app.storage.user["authenticated"] = True
    app.storage.user["usuario_id"] = usuario.id
    app.storage.user["nome_usuario"] = usuario.nome_usuario
    app.storage.user["iniciais"] = usuario.iniciais


def logout_usuario() -> None:
    app.storage.user.clear()


def obter_usuario_logado() -> Optional[dict[str, str]]:
    if not app.storage.user.get("authenticated", False):
        return None
    nome = app.storage.user.get("nome_usuario", "conferente")
    iniciais = app.storage.user.get("iniciais", nome[:2].upper())
    return {
        "id": app.storage.user.get("usuario_id", ""),
        "nome_usuario": nome,
        "iniciais": iniciais,
    }
