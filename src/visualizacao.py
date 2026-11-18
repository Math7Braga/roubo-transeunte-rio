"""Figuras: estáticas (matplotlib -> PNG) e interativas (Plotly -> HTML)."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go

from .analise import MESES_PT, MESES_EXT, pivot_mensal

# Paleta Okabe-Ito (distinguível por daltônicos)
AZUL, LARANJA, VERDE, VERMELHO, CINZA = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#6b7280"
fmt_mil = lambda v, _=None: f"{v:,.0f}".replace(",", ".")


def fig_evolucao_anual(anual):
    """Figura 1 (estática): total anual (barras) e taxa por 100 mil hab. (linha)."""
    c = anual[anual["ano_completo"]]
    fig, ax = plt.subplots(figsize=(9, 5.0), dpi=200)
    ax.bar(c["ano"], c["total_calculado"], color=AZUL, alpha=.85, label="Ocorrências (total do ano)")
    ax.set_ylabel("Ocorrências por ano")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(fmt_mil))
    ax.set_xticks(c["ano"][::2]); ax.tick_params(axis="x", rotation=45)
    ax.spines[["top"]].set_visible(False)
    handles, labels = ax.get_legend_handles_labels()
    ct = c.dropna(subset=["taxa_100k_calculada"])
    if len(ct) >= 3:
        ax2 = ax.twinx()
        ax2.plot(ct["ano"], ct["taxa_100k_calculada"], color=VERMELHO, lw=2.2, marker="o", ms=3.5,
                 label="Taxa por 100 mil habitantes")
        ax2.set_ylabel("Taxa por 100 mil habitantes"); ax2.set_ylim(bottom=0)
        ax2.spines[["top"]].set_visible(False)
        h2, l2 = ax2.get_legend_handles_labels(); handles += h2; labels += l2
    ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
    ax.set_title("Roubo a transeunte no Município do Rio de Janeiro — anos completos", loc="left", fontsize=11)
    fig.tight_layout()
    return fig


def fig_sazonalidade(saz):
    """Figura 3 (estática): índice sazonal médio por mês, com desvio-padrão."""
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=200)
    cores = [VERMELHO if v == saz["indice_medio"].max() else AZUL if v >= 1 else CINZA
             for v in saz["indice_medio"]]
    # barras partem da linha 1,00 (média do ano): mostram o desvio em relação à média, sem truncar o eixo
    ax.bar(saz["mes"], saz["indice_medio"] - 1, bottom=1, color=cores, alpha=.9)
    ax.errorbar(saz["mes"], saz["indice_medio"], yerr=saz["desvio"], fmt="none", ecolor="black", capsize=3, lw=1.2)
    ax.axhline(1, color="black", lw=1, ls="--")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels([m.capitalize() for m in MESES_PT])
    ax.set_ylabel("Índice sazonal (1,00 = média do ano)")
    ax.set_ylim(float((saz["indice_medio"] - saz["desvio"]).min()) - .05, float((saz["indice_medio"] + saz["desvio"]).max()) + .05)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Padrão sazonal médio (anos completos); barras de erro = ±1 desvio-padrão",
                 loc="left", fontsize=11)
    fig.tight_layout()
    return fig


_CFG = {"responsive": True, "displaylogo": False}


def fig_heatmap(mensal):
    """Figura 2 (interativa): mapa de calor ano x mês."""
    p = pivot_mensal(mensal)
    texto = [[fmt_mil(v) if v == v else "sem dado" for v in linha] for linha in p.to_numpy()]
    fig = go.Figure(go.Heatmap(
        z=p.to_numpy(), x=[m.capitalize() for m in MESES_PT], y=p.index.astype(str),
        colorscale="YlOrRd", colorbar={"title": "Ocorrências"}, text=texto,
        hovertemplate="%{y} — %{x}<br>%{text} ocorrências<extra></extra>"))
    fig.update_yaxes(autorange="reversed", dtick=2)
    fig.update_layout(template="plotly_white", height=520, margin=dict(l=50, r=10, t=30, b=40),
                      title=dict(text="Ocorrências mensais por ano e mês", x=0, font=dict(size=14)))
    return fig


def fig_pandemia(cp):
    """Figura 4 (interativa): razão mensal em relação à média do período-base."""
    r = cp["razoes"]
    cores = {2020: VERMELHO, 2021: LARANJA, 2022: AZUL}
    fig = go.Figure()
    for ano in r.columns:
        fig.add_scatter(x=[m.capitalize() for m in MESES_PT], y=r[ano].to_numpy(), mode="lines+markers",
                        name=str(ano), line=dict(color=cores.get(ano, CINZA), width=2.5),
                        hovertemplate=f"{ano} — %{{x}}<br>%{{y:.0%}} da mediana do período-base<extra></extra>")
    fig.add_hline(y=1, line_dash="dash", line_color="black")
    b = cp["anos_base"]
    fig.update_layout(template="plotly_white", height=420, margin=dict(l=50, r=10, t=30, b=40),
                      yaxis=dict(title=f"Razão (1,00 = mediana {b[0]}–{b[-1]})", tickformat=".0%"),
                      legend=dict(orientation="h", y=-0.15),
                      title=dict(text=f"Ocorrências mensais relativas à mediana de {b[0]}–{b[-1]}",
                                 x=0, font=dict(size=14)))
    return fig


def html_plotly(fig, div_id):
    """Fragmento HTML (o <script> do Plotly é carregado uma vez pela página)."""
    return fig.to_html(full_html=False, include_plotlyjs=False, config=_CFG, div_id=div_id)
