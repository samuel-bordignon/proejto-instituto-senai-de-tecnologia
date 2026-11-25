"""Testes de integração com PostgreSQL/Supabase: Isolamento SQL, Duplicidade e Auditoria RN-10 (CT-11, CT-16)."""

from __future__ import annotations

from datetime import date
import io
from pathlib import Path
import re

import openpyxl
import pytest

from app.core.models import ResultadoPreLeitura
from app.repo import PostgresRepository
from app.services.pdf_service import gerar_pdf_amostra
from app.services.xlsx_service import gerar_xlsx_amostra
from database import listar_todas_queries


def test_rnf06_zero_sql_fora_de_database_queries() -> None:
    """RNF-06: Garante que nenhuma query SQL esteja embutida em arquivos Python de app/ ou database/."""
    repo_root = Path(__file__).resolve().parent.parent
    inv = listar_todas_queries()
    assert {"auth", "cadastros", "base_legal", "amostras", "conferencia", "analise_local"}.issubset(inv.keys())

    padrao_sql = re.compile(
        r"""(['"])\s*(SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b""",
        re.IGNORECASE,
    )
    violacoes: list[str] = []
    for pasta in (repo_root / "database", repo_root / "app"):
        for arq in pasta.rglob("*.py"):
            for idx, linha in enumerate(arq.read_text(encoding="utf-8").splitlines(), start=1):
                if padrao_sql.search(linha):
                    violacoes.append(f"{arq.relative_to(repo_root)}:{idx}")
    assert not violacoes, f"Queries SQL encontradas fora de database/queries/: {violacoes}"


def test_ct11_rejeicao_transacional_reimportacao_banco(db_repo: PostgresRepository) -> None:
    """CT-11: Tentativa de gravar código de amostra já existente no PostgreSQL é bloqueada."""
    propostas = db_repo.listar_propostas("Cervejaria Vale do Itajaí Ltda")
    prop_ete = next(p for p in propostas if "CONAMA 430" in p)

    pre_existente = ResultadoPreLeitura(
        nome_arquivo="reimport.csv",
        codigo_amostra_principal="63450/2026",
        data_coleta=date(2026, 7, 15),
        data_conclusao=date(2026, 7, 27),
        valores_brutos={794: "7,91", 106: "71"},
    )

    with pytest.raises(ValueError, match="63450/2026"):
        db_repo.criar_amostra_importada(
            pre_leitura=pre_existente,
            cliente="Cervejaria Vale do Itajaí Ltda",
            proposta=prop_ete,
            local_coleta="Saída — Efluente Sanitário (ETE 01)",
            origem="Efluente Tratado",
            normas_selecionadas=[("CONAMA 430", "Sem Classe (Art. 16)")],
            usuario="samuel.wiegand",
        )


def test_ct16_alteracao_manual_e_auditoria_log_alteracao(db_repo: PostgresRepository) -> None:
    """
    CT-16: Conferente altera 1 ensaio (Pendente -> Conforme) sem justificativa obrigatória,
    provocando recálculo derivado do status geral + edita o texto da minuta; grava em log_alteracao
    (fk_resultado_amostra preenchido p/ ensaio e NULL p/ parecer_geral e minuta) e exporta em PDF/XLSX.
    """
    cod_temp = "99999/2026"
    db_repo.excluir_amostra(cod_temp)

    propostas = db_repo.listar_propostas("Cervejaria Vale do Itajaí Ltda")
    prop_ete = next(p for p in propostas if "CONAMA 430" in p)

    try:
        pre = ResultadoPreLeitura(
            nome_arquivo="ct16_audit.csv",
            codigo_amostra_principal=cod_temp,
            data_coleta=date(2026, 7, 30),
            data_conclusao=date(2026, 7, 31),
            valores_brutos={
                794: "7,35",   # Conforme (5 a 9)
                106: "<25,0",  # Pendente (<LQ acima de VMP 20,0)
                93: "110",     # Sem VMP -> gravado apenas em resultado_amostra p/ histórico
            },
        )
        criada = db_repo.criar_amostra_importada(
            pre_leitura=pre,
            cliente="Cervejaria Vale do Itajaí Ltda",
            proposta=prop_ete,
            local_coleta="Saída — Efluente Sanitário (ETE 01)",
            origem="Efluente Tratado",
            normas_selecionadas=[
                ("CONAMA 430", "Sanitário (Art. 21)"),
                ("CONAMA 430", "Sem Classe (Art. 16)"),
            ],
            usuario="samuel.wiegand",
        )
        assert criada.status_geral == "Pendente"
        assert len(criada.ensaios) == 2

        minuta_custom = (
            "Os resultados de ensaio atendem às especificações aplicadas neste documento "
            "(revisado e liberado para o PRL)."
        )

        # Salva SEM observação/justificativa obrigatória no ensaio 106!
        pos_conf, qtd_logs = db_repo.salvar_conferencia(
            codigo=cod_temp,
            edicoes_status={794: "Conforme", 106: "Conforme"},
            edicoes_obs={794: "", 106: ""},
            novo_parecer=minuta_custom,
            usuario="bruno.dombroski",
        )
        assert qtd_logs == 3
        assert pos_conf.status_geral == "Favorável"
        assert pos_conf.parecer == minuta_custom

        # Recarrega do banco (equivalente a F5 no navegador) e valida trilha RN-10
        recarregada = db_repo.obter_amostra(cod_temp)
        assert recarregada is not None
        assert recarregada.status_geral == "Favorável"
        assert recarregada.parecer == minuta_custom
        assert len(recarregada.logs) == 3

        por_campo = {lg.campo_alterado: lg for lg in recarregada.logs}
        assert set(por_campo.keys()) == {"conformidade", "parecer_geral", "minuta"}

        assert por_campo["conformidade"].ensaio_codigo == 106
        assert por_campo["conformidade"].valor_anterior == "Pendente"
        assert por_campo["conformidade"].valor_novo == "Conforme"
        assert por_campo["conformidade"].observacao is None
        assert por_campo["conformidade"].usuario == "bruno.dombroski"

        assert por_campo["parecer_geral"].ensaio_codigo is None
        assert por_campo["parecer_geral"].valor_anterior == "Pendente"
        assert por_campo["parecer_geral"].valor_novo == "Favorável"

        assert por_campo["minuta"].ensaio_codigo is None
        assert por_campo["minuta"].valor_novo == minuta_custom

        # Verifica presença da trilha no XLSX e geração limpa do PDF
        pdf_b = gerar_pdf_amostra(recarregada)
        assert pdf_b.startswith(b"%PDF")
        wb = openpyxl.load_workbook(io.BytesIO(gerar_xlsx_amostra(recarregada)))
        ws_hist = wb["Historico_RN10"]
        linhas_hist = [
            [cell.value for cell in row]
            for row in ws_hist.iter_rows(min_row=2)
            if any(cell.value is not None for cell in row)
        ]
        assert len(linhas_hist) == 3
        assert any("bruno.dombroski" in str(r) for r in linhas_hist)
    finally:
        db_repo.excluir_amostra(cod_temp)
        assert db_repo.obter_amostra(cod_temp) is None
