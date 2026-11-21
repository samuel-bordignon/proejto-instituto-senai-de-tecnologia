"""Tabela interativa de ensaios da Tela B4 (/amostra/{codigo}) com 1–3 normas, menu de status e observação inline."""

from __future__ import annotations

from typing import Callable

from nicegui import ui

from app.core.config import STATUS_CONFORME, STATUS_NAO_CONFORME, STATUS_PENDENTE
from app.core.models import Amostra
from app.ui.components.badges import status_pill_html, variante_status_ensaio


def montar_rows_tabela_ensaios(amostra: Amostra, ensaio_selecionado: int) -> list[dict]:
    """Serializa os ensaios da amostra para o formato esperado pela tabela Quasar da B4."""
    rows: list[dict] = []
    for e in amostra.ensaios:
        variante_st = variante_status_ensaio(e.status)
        pill_st = status_pill_html(f"{e.status.upper()} ▾", variante_st, clickable=True)

        if e.sinalizacao and e.sinalizacao_tipo:
            pill_sinal = status_pill_html(e.sinalizacao, f"outline-{e.sinalizacao_tipo}")  # type: ignore[arg-type]
        else:
            pill_sinal = '<span class="text-[12px] text-[#71717A]">—</span>'

        row: dict = {
            "codigo": e.codigo,
            "nome": e.nome,
            "resultado": e.resultado_formatado,
            "is_nc": e.status == STATUS_NAO_CONFORME,
            "is_active": e.codigo == ensaio_selecionado,
            "status": e.status,
            "status_html": pill_st,
            "sinalizacao_html": pill_sinal,
            "observacao": e.observacao,
        }
        for idx, norma in enumerate(amostra.normas):
            av = e.avaliacoes.get(norma.id)
            row[f"norma_{idx}"] = av.vmp_texto if av else "—"
        rows.append(row)
    return rows


def criar_tabela_ensaios(
    amostra: Amostra,
    ensaio_selecionado: int,
    on_select_row: Callable,
    on_status_change: Callable,
    on_obs_change: Callable,
) -> ui.table:
    """Cria a tabela Quasar de ensaios com colunas dinâmicas (1–3 normas), menu de status e input inline."""
    normas_cols_meta = [
        {
            "name": f"norma_{i}",
            "label": n.titulo_coluna.upper(),
            "field": f"norma_{i}",
            "align": "left",
        }
        for i, n in enumerate(amostra.normas)
    ]

    columns = (
        [
            {"name": "codigo", "label": "CÓD.", "field": "codigo", "align": "left"},
            {"name": "nome", "label": "ENSAIO", "field": "nome", "align": "left"},
            {"name": "resultado", "label": "RESULTADO", "field": "resultado", "align": "left"},
        ]
        + normas_cols_meta
        + [
            {"name": "status", "label": "STATUS", "field": "status", "align": "left"},
            {"name": "sinalizacao", "label": "SINALIZAÇÃO", "field": "sinalizacao_html", "align": "left"},
            {"name": "observacao", "label": "OBSERVAÇÃO", "field": "observacao", "align": "left"},
        ]
    )

    n_normas = len(amostra.normas)
    w_norma_min = "128px" if n_normas == 3 else "148px"
    norma_tds = "\n".join(
        f"""
        <q-td key="norma_{i}" :props="props" style="min-width:{w_norma_min};">
          <span class="font-mono-lt text-[12px] text-[#52525B]">{{{{ props.row.norma_{i} }}}}</span>
        </q-td>
        """
        for i in range(n_normas)
    )

    tabela = (
        ui.table(
            columns=columns,
            rows=montar_rows_tabela_ensaios(amostra, ensaio_selecionado),
            row_key="codigo",
            pagination={"rowsPerPage": 0},
        )
        .props("flat hide-bottom")
        .classes("w-full lt-table")
    )

    tabela.add_slot(
        "body",
        f"""
        <q-tr
          :props="props"
          :class="props.row.is_active ? 'lt-row-active cursor-pointer' : 'cursor-pointer'"
          @click="$parent.$emit('select_row', props.row.codigo)"
        >
          <q-td key="codigo" :props="props" style="width:68px;">
            <span :class="props.row.is_active ? 'font-mono-lt text-[12px] font-bold text-[#111827]' : 'font-mono-lt text-[12px] font-medium text-[#52525B]'">
              {{{{ props.row.codigo }}}}
            </span>
          </q-td>

          <q-td key="nome" :props="props" style="min-width:180px;">
            <span :class="props.row.is_active ? 'text-[13px] font-bold text-[#111827]' : 'text-[13px] font-medium text-[#111827]'">
              {{{{ props.row.nome }}}}
            </span>
          </q-td>

          <q-td key="resultado" :props="props" style="min-width:118px;">
            <span :class="props.row.is_nc ? 'font-mono-lt text-[12px] font-bold text-[#DC2626]' : 'font-mono-lt text-[12px] font-medium text-[#111827]'">
              {{{{ props.row.resultado }}}}
            </span>
          </q-td>

          {norma_tds}

          <q-td key="status" :props="props" style="min-width:155px;" @click.stop>
            <div class="inline-block">
              <div v-html="props.row.status_html"></div>
              <q-menu auto-close anchor="bottom left" self="top left" :offset="[0, 6]">
                <q-list dense style="min-width: 175px; padding: 4px;">
                  <q-item clickable v-close-popup @click="$parent.$emit('status_change', {{ codigo: props.row.codigo, status: '{STATUS_CONFORME}' }})" class="rounded-[6px]">
                    <q-item-section avatar style="min-width:22px; padding-right:6px;">
                      <span style="width:8px; height:8px; border-radius:999px; background:#16A34A; display:inline-block;"></span>
                    </q-item-section>
                    <q-item-section class="text-[12px] font-semibold text-[#111827]">Conforme</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="$parent.$emit('status_change', {{ codigo: props.row.codigo, status: '{STATUS_NAO_CONFORME}' }})" class="rounded-[6px]">
                    <q-item-section avatar style="min-width:22px; padding-right:6px;">
                      <span style="width:8px; height:8px; border-radius:999px; background:#DC2626; display:inline-block;"></span>
                    </q-item-section>
                    <q-item-section class="text-[12px] font-semibold text-[#111827]">Não conforme</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="$parent.$emit('status_change', {{ codigo: props.row.codigo, status: '{STATUS_PENDENTE}' }})" class="rounded-[6px]">
                    <q-item-section avatar style="min-width:22px; padding-right:6px;">
                      <span style="width:8px; height:8px; border-radius:999px; background:#D97706; display:inline-block;"></span>
                    </q-item-section>
                    <q-item-section class="text-[12px] font-semibold text-[#111827]">Pendente</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
            </div>
          </q-td>

          <q-td key="sinalizacao" :props="props" style="min-width:158px;">
            <div v-html="props.row.sinalizacao_html"></div>
          </q-td>

          <q-td key="observacao" :props="props" style="min-width:140px;" @click.stop>
            <input
              type="text"
              class="lt-obs-input"
              :value="props.row.observacao"
              placeholder="—"
              @change="$parent.$emit('obs_change', {{ codigo: props.row.codigo, obs: $event.target.value }})"
            />
          </q-td>
        </q-tr>
        """,
    )

    tabela.on("select_row", on_select_row)
    tabela.on("status_change", on_status_change)
    tabela.on("obs_change", on_obs_change)
    return tabela
