"""Configuração compartilhada do pytest para a suíte oficial CT-01 a CT-16."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.repo import PostgresRepository, repo
from database import close_pool


@pytest.fixture(scope="session")
def db_repo() -> PostgresRepository:
    """Retorna o singleton PostgresRepository aquecido contra o Supabase."""
    repo.recarregar_catalogo()
    return repo


def pytest_sessionfinish(session, exitstatus) -> None:
    """Fecha o pool de conexões de forma limpa ao encerrar a suíte."""
    close_pool()
