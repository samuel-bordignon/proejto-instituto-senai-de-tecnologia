"""Testes automatizados do Parser UltraLIMS, Duplicidade e Exportação PDF/XLSX (CT-10, CT-11, RF-07)."""

from __future__ import annotations

import io
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from app.core.parser_ultralims import analisar_lote_ultralims
from app.repo import PostgresRepository
from app.services.pdf_service import gerar_pdf_amostra
from app.services.xlsx_service import gerar_xlsx_amostra


def test_ct10_sujeira_real_ultralims_e_ensaios_sem_match(db_repo: PostgresRepository) -> None:
    """
    CT-10: Planilha com ' 1.408,00', '>2.500.000.000', '<0,060', '7,91', '________',
    'Resultado na carta controle de SVOC', sem Data Conclusão e colunas sem VMP (93, 28, 33).
    """
    csv_conteudo = (
        "Código da Amostra;Data Coleta;Data Conclusão;"
        "794 - pH;106 - Nitrogênio Amoniacal;59 - Coliformes Termotolerantes;"
        "259 - Chumbo Total;800 - Temperatura;119 - Sólidos Sedimentáveis;"
        "93 - DQO;28 - Fósforo Total;33 - Nitrogênio Amoniacal Total\n"
        "79001/2026;20/07/2026;;"
        "7,91; 1.408,00;>2.500.000.000;"
        "<0,060;________;Resultado na carta controle de SVOC;"
        "125;0,08;2,4\n"
    ).encode("utf-8")

    lote = db_repo.analisar_planilha(
        arquivo_bytes=csv_conteudo,
        nome_arquivo="ct10_sujeira.csv",
        origem="Água Superficial (Água doce)",
        normas_selecionadas=[("CONAMA 357", "Classe 1")],
    )
    assert len(lote.amostras) == 1
    pre = lote.amostras[0]

    # Ignorados RN-02: '________' e 'Resultado na carta controle de SVOC'
    assert pre.total_ignorados == 2
    ensaios_ignorados = {i.ensaio_coluna for i in pre.itens_por_kpi["ignorados"]}
    assert any("800" in c for c in ensaios_ignorados)
    assert any("119" in c for c in ensaios_ignorados)

    # Sem VMP na CONAMA 357 Classe 1: 794 (pH de efluente), 106, 93, 28 e 33 (28 e 33 excluídos na Camada 1!)
    cods_sem_vmp = {int(i.ensaio_coluna.split("·")[0].strip()) for i in pre.itens_por_kpi["sem_vmp"]}
    assert {93, 28, 33}.issubset(cods_sem_vmp)

    # Avisos: Data Conclusão vazia + sujeira real em 106 (' 1.408,00') e 59 ('>2.500.000.000')
    # '7,91' e '<0,060' NÃO devem gerar falso aviso de limpeza numérica!
    avisos = pre.itens_por_kpi["avisos"]
    textos_avisos = [f"{a.ensaio_coluna}: {a.acao_motor}" for a in avisos]
    assert any("Data Conclusão vazia" in a.valor_bruto for a in avisos)
    assert any("106 ·" in t and "Limpeza numérica RN-01" in t for t in textos_avisos)
    assert any("59 ·" in t and "Limpeza numérica RN-01" in t for t in textos_avisos)
    assert not any("794 ·" in t and "Limpeza numérica RN-01" in t for t in textos_avisos)
    assert not any("259 ·" in t and "Limpeza numérica RN-01" in t for t in textos_avisos)


def test_ct11_deteccao_duplicidade_banco_e_lote(db_repo: PostgresRepository) -> None:
    """CT-11: Reimportar 63450/2026 já existente no PostgreSQL ou repetida no arquivo marca DUPLICADA."""
    csv_dup = (
        "Código da Amostra;Data Coleta;Data Conclusão;794 - pH;106 - Nitrogênio Amoniacal\n"
        "63450/2026;15/07/2026;27/07/2026;7,91;71\n"
        "79055/2026;16/07/2026;27/07/2026;7,20;10\n"
        "79055/2026;16/07/2026;27/07/2026;7,20;10\n"
    ).encode("utf-8")

    lote = db_repo.analisar_planilha(
        arquivo_bytes=csv_dup,
        nome_arquivo="ct11_dup.csv",
        origem="Efluente Tratado",
        normas_selecionadas=[("CONAMA 430", "Sem Classe (Art. 16)")],
    )
    assert len(lote.amostras) == 3
    assert lote.amostras[0].duplicada is True
    assert any(a.classificacao == "DUPLICADA" for a in lote.amostras[0].itens_por_kpi["avisos"])
    assert lote.amostras[1].duplicada is False
    assert lote.amostras[2].duplicada is True  # repetida no mesmo lote


def test_planilha_real_ultralims_e_exportacoes_pdf_xlsx(db_repo: PostgresRepository) -> None:
    """Testa leitura de fatia da planilha real do IST + geração de PDF e XLSX com 3 abas (RF-07 / RNF-02)."""
    planilha_real = (
        Path(__file__).resolve().parent.parent.parent
        / "docs"
        / "planilhas"
        / "Tela_GerenciaAmostra_ResultadoColuna (1) (1).xlsx"
    )
    if planilha_real.exists():
        df_full = pd.read_excel(planilha_real, dtype=str)
        # Seleciona a linha real da amostra 63450/2026 e serializa como .xlsx em memória
        col_cod = next(c for c in df_full.columns if "amostra" in str(c).lower() and "extern" not in str(c).lower())
        df_slice = df_full[df_full[col_cod].astype(str).str.strip() == "63450/2026"].head(1)
        buf = io.BytesIO()
        df_slice.to_excel(buf, index=False)
        lote_real = db_repo.analisar_planilha(
            arquivo_bytes=buf.getvalue(),
            nome_arquivo=planilha_real.name,
            origem="Efluente Tratado",
            normas_selecionadas=[("CONAMA 430", "Sanitário (Art. 21)"), ("CONAMA 430", "Sem Classe (Art. 16)")],
        )
        assert len(lote_real.amostras) == 1
        assert lote_real.amostras[0].codigo_amostra_principal == "63450/2026"
        assert lote_real.amostras[0].total_mapeados == 14
        assert lote_real.amostras[0].duplicada is True  # já populada no banco!

    # Valida exportações PDF e XLSX da amostra 67019/2026 (preservação de unidades µg/L vs mg/L — RNF-02)
    am67019 = db_repo.obter_amostra("67019/2026")
    assert am67019 is not None
    pdf_bytes = gerar_pdf_amostra(am67019)
    assert pdf_bytes.startswith(b"%PDF") and len(pdf_bytes) > 1500

    xlsx_bytes = gerar_xlsx_amostra(am67019)
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    assert wb.sheetnames == ["Resumo e Parecer", "Resultados e Conformidade", "Historico_RN10"]
    ws_res = wb["Resultados e Conformidade"]
    textos_celulas = [
        str(cell.value)
        for row in ws_res.iter_rows()
        for cell in row
        if cell.value is not None
    ]
    assert any("µg/L" in t for t in textos_celulas)
    assert any("mg/L" in t for t in textos_celulas)

    # Valida que arquivo inválido levanta erro claro
    with pytest.raises(ValueError):
        analisar_lote_ultralims(b"colA;colB\n1;2\n", "invalido.csv", catalogo_ensaios={794: {"nome": "pH", "unidade": "", "tipo": "AUTOMATICA"}})
