"""Entry point da aplicação LaudoTech em NiceGUI conectada ao PostgreSQL/Supabase."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Garante a raiz do repositório (proejto-instituto-senai-de-tecnologia) no sys.path
PASTA_APP = Path(__file__).resolve().parent
RAIZ_REPO = PASTA_APP.parent
if str(RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPO))

from nicegui import app, ui

from app.ui.auth import AuthMiddleware
from app.ui.pages.analise_local import registrar_pagina_analise_local
from app.ui.pages.conferencia import registrar_pagina_conferencia
from app.ui.pages.importar import registrar_pagina_importar
from app.ui.pages.login import registrar_pagina_login
from app.ui.pages.painel import registrar_pagina_painel
from database import close_pool

# Assets estáticos (foto FIESC/SENAI e ícone oficial LaudoTech)
PASTA_ASSETS = PASTA_APP / "assets"
app.add_static_files("/assets", str(PASTA_ASSETS))

# Middleware de proteção de sessão (RF-01) e liberação limpa do pool no encerramento
app.add_middleware(AuthMiddleware)
app.on_shutdown(close_pool)

# Registro das 5 rotas da POC
registrar_pagina_login()          # /login
registrar_pagina_painel()         # /
registrar_pagina_importar()       # /importar
registrar_pagina_conferencia()    # /amostra/{codigo}
registrar_pagina_analise_local()  # /analise


def main() -> None:
    porta = int(os.getenv("LAUDOTECH_PORT", "8080"))
    ui.run(
        title="LaudoTech — IST Ambiental",
        favicon=str(PASTA_ASSETS / "laudotech_logo_icon.png"),
        host="127.0.0.1",
        port=porta,
        storage_secret=os.getenv("LAUDOTECH_STORAGE_SECRET", "laudotech-ist-poc-secret-2026"),
        reload=False,
        show=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
