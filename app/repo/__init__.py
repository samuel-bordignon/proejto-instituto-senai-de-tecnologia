"""Pacote de repositórios do LaudoTech — produção exclusivamente PostgreSQL/Supabase."""

from app.repo.base import RepositorioLaudoTech
from app.repo.postgres_repo import PostgresRepository, repo

__all__ = [
    "PostgresRepository",
    "RepositorioLaudoTech",
    "repo",
]
