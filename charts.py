"""Gráficos (Plotly) com um tema único e consistente."""
import pandas as pd
import plotly.graph_objects as go

# Paleta categórica (ordem fixa, validada para daltonismo nos pares adjacentes)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
RECEITA = SERIES[0]   # azul
DESPESA = SERIES[1]   # laranja
GUARDADO = SERIES[2]  # verde-água

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
CRITICAL = "#d03b3b"

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
CONFIG = {"displayModeBar": False, "locale": "pt-BR"}


def brl(v):
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-R$ " if v < 0 else "R$ ") + s


MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _eixo_meses(fig, datas, max_rotulos=7):
    """Rótulos de mês em português (ex.: out/26)."""
    datas = sorted(pd.to_datetime(pd.Series(datas)).dt.to_period("M").dt.to_timestamp().unique())
    passo = max(1, -(-len(datas) // max_rotulos))
    vals = datas[::passo]
    fig.update_xaxes(tickvals=vals, ticktext=[MESES[d.month - 1] + "/" + str(d.year)[2:] for d in vals],
                     tickangle=0)


def _layout(fig, height=360, legend=True):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=13, color=INK_2),
        separators=",.",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text="",
                    font=dict(color=INK_2)),
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(family=FONT, color=INK)),
        barcornerradius=4,
        bargap=0.35,
        bargroupgap=0.08,
    )
    fig.update_xaxes(showgrid=False, linecolor=BASELINE, tickfont=dict(color=MUTED), ticks="")
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=BASELINE,
                     tickfont=dict(color=MUTED), tickprefix="R$ ", tickformat=",.0f")
    return fig


def _vazio(msg="Sem dados ainda"):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(color=MUTED, size=14))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _layout(fig, height=220, legend=False)


def resumo_mensal(trans):
    """DataFrame com receitas, despesas e saldo por mês."""
    if trans.empty:
        return pd.DataFrame(columns=["mes", "receita", "despesa", "saldo"])
    t = trans.copy()
    t["mes"] = t["data"].dt.to_period("M").dt.to_timestamp()
    pv = t.pivot_table(index="mes", columns="tipo", values="valor", aggfunc="sum", fill_value=0)
    for c in ("receita", "despesa"):
        if c not in pv:
            pv[c] = 0.0
    pv["saldo"] = pv["receita"] - pv["despesa"]
    return pv.reset_index()[["mes", "receita", "despesa", "saldo"]]


def receitas_vs_despesas(trans):
    m = resumo_mensal(trans)
    if m.empty:
        return _vazio()
    fig = go.Figure()
    fig.add_bar(x=m["mes"], y=m["receita"], name="Receitas", marker_color=RECEITA,
                hovertemplate="Receitas: R$ %{y:,.2f}<extra></extra>")
    fig.add_bar(x=m["mes"], y=m["despesa"], name="Despesas", marker_color=DESPESA,
                hovertemplate="Despesas: R$ %{y:,.2f}<extra></extra>")
    fig.add_scatter(x=m["mes"], y=m["saldo"], name="Saldo do mês", mode="lines+markers",
                    line=dict(color=INK, width=2), marker=dict(size=8, color=INK,
                                                               line=dict(color=SURFACE, width=2)),
                    hovertemplate="Saldo: R$ %{y:,.2f}<extra></extra>")
    fig.update_layout(barmode="group", hovermode="x unified")
    fig.update_xaxes(hoverformat="%m/%Y")
    _eixo_meses(fig, m["mes"], max_rotulos=13)
    return _layout(fig)


def barras_horizontais(nomes, valores, cor=SERIES[0], height=None, hover_label="Valor"):
    df = pd.DataFrame({"nome": nomes, "valor": valores}).sort_values("valor")
    if df.empty or df["valor"].sum() == 0:
        return _vazio()
    fig = go.Figure(go.Bar(
        x=df["valor"], y=df["nome"], orientation="h", marker_color=cor,
        text=[brl(v) for v in df["valor"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=INK_2),
        hovertemplate="%{y}<br>" + hover_label + ": R$ %{x:,.2f}<extra></extra>",
    ))
    _layout(fig, height=height or max(220, 44 * len(df) + 40), legend=False)
    fig.update_xaxes(showgrid=True, gridcolor=GRID, tickprefix="R$ ", tickformat=",.0f",
                     range=[0, df["valor"].max() * 1.4])
    fig.update_yaxes(showgrid=False, tickprefix="", tickfont=dict(color=INK_2))
    return fig


def despesas_por_categoria(trans):
    d = trans[trans["tipo"] == "despesa"].groupby("categoria")["valor"].sum()
    return barras_horizontais(d.index, d.values, cor=DESPESA, hover_label="Gasto")


def receitas_por_categoria(trans):
    d = trans[trans["tipo"] == "receita"].groupby("categoria")["valor"].sum()
    return barras_horizontais(d.index, d.values, cor=RECEITA, hover_label="Recebido")


def saldo_acumulado(trans):
    if trans.empty:
        return _vazio()
    t = trans.sort_values("data").copy()
    t["sinal"] = t["valor"].where(t["tipo"] == "receita", -t["valor"])
    diario = t.groupby("data")["sinal"].sum().cumsum()
    fig = go.Figure(go.Scatter(
        x=diario.index, y=diario.values, mode="lines", line=dict(color=RECEITA, width=2),
        fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
        hovertemplate="%{x|%d/%m/%Y}<br>Saldo acumulado: R$ %{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(hovermode="x")
    return _layout(fig, legend=False)


def reservas_progresso(res):
    """Barras de saldo por área, com marcador da meta."""
    if res.empty:
        return _vazio("Nenhuma área de reserva cadastrada")
    r = res.sort_values("saldo")
    fig = go.Figure()
    fig.add_bar(x=r["saldo"], y=r["nome"], orientation="h", name="Guardado",
                marker_color=GUARDADO, text=[brl(v) for v in r["saldo"]],
                textposition="outside", cliponaxis=False, textfont=dict(color=INK_2),
                customdata=r["meta"],
                hovertemplate="%{y}<br>Guardado: R$ %{x:,.2f}<br>Meta: R$ %{customdata:,.2f}<extra></extra>")
    com_meta = r[r["meta"] > 0]
    if not com_meta.empty:
        fig.add_scatter(x=com_meta["meta"], y=com_meta["nome"], mode="markers", name="Meta",
                        marker=dict(symbol="line-ns", size=22, color=INK, line=dict(width=3, color=INK)),
                        hovertemplate="%{y}<br>Meta: R$ %{x:,.2f}<extra></extra>")
    _layout(fig, height=max(240, 52 * len(r) + 60))
    top = max(r["saldo"].max(), r["meta"].max())
    fig.update_xaxes(showgrid=True, gridcolor=GRID, tickprefix="R$ ", tickformat=",.0f",
                     range=[0, top * 1.4])
    fig.update_yaxes(showgrid=False, tickprefix="", tickfont=dict(color=INK_2))
    return fig


def evolucao_reservas(mov, reservas):
    """Área empilhada do saldo de cada reserva ao longo do tempo."""
    if mov.empty:
        return _vazio()
    m = mov.copy()
    m["mes"] = m["data"].dt.to_period("M").dt.to_timestamp()
    pv = m.pivot_table(index="mes", columns="nome", values="valor", aggfunc="sum", fill_value=0)
    pv = pv.sort_index().cumsum()
    fig = go.Figure()
    # cor fixa por entidade (ordem de cadastro), nunca pelo ranking
    nomes = list(reservas.sort_values("id")["nome"])
    for i, nome in enumerate(nomes):
        if nome not in pv:
            continue
        cor = SERIES[i] if i < len(SERIES) else MUTED
        fig.add_scatter(x=pv.index, y=pv[nome], name=nome, mode="lines", stackgroup="r",
                        line=dict(width=2, color=cor),
                        hovertemplate=nome + ": R$ %{y:,.2f}<extra></extra>")
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(hoverformat="%m/%Y")
    _eixo_meses(fig, pv.index)
    return _layout(fig)


def dividas_saldo(div):
    if div.empty:
        return _vazio("Nenhuma dívida cadastrada")
    d = div.sort_values("saldo")
    fig = go.Figure()
    fig.add_bar(x=d["pago"], y=d["nome"], orientation="h", name="Já pago",
                marker_color=RECEITA, hovertemplate="%{y}<br>Pago: R$ %{x:,.2f}<extra></extra>")
    fig.add_bar(x=d["saldo"], y=d["nome"], orientation="h", name="Falta pagar",
                marker_color=DESPESA, hovertemplate="%{y}<br>Falta: R$ %{x:,.2f}<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.4, legend_traceorder="normal")
    fig.update_traces(marker_line=dict(color=SURFACE, width=2))
    _layout(fig, height=max(240, 52 * len(d) + 60))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, tickprefix="R$ ", tickformat=",.0f")
    fig.update_yaxes(showgrid=False, tickprefix="", tickfont=dict(color=INK_2))
    return fig


def evolucao_dividas(div, pag):
    """Saldo devedor total ao longo do tempo (valor original - pagamentos)."""
    if div.empty:
        return _vazio()
    eventos = [(pd.Timestamp(r.data_inicio), r.valor_original) for r in div.itertuples()]
    eventos += [(r.data, -r.valor) for r in pag.itertuples()]
    s = pd.DataFrame(eventos, columns=["data", "delta"]).groupby("data")["delta"].sum().sort_index().cumsum()
    fig = go.Figure(go.Scatter(
        x=s.index, y=s.clip(lower=0).values, mode="lines", line=dict(color=DESPESA, width=2, shape="hv"),
        hovertemplate="%{x|%d/%m/%Y}<br>Saldo devedor: R$ %{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(hovermode="x")
    _eixo_meses(fig, s.index)
    return _layout(fig, legend=False)


def contas_proximas(contas):
    """Contas em aberto por data de vencimento; vencidas destacadas."""
    abertas = contas[~contas["pago"]].sort_values("vencimento")
    if abertas.empty:
        return _vazio("Nenhuma conta em aberto")
    hoje = pd.Timestamp.today().normalize()
    vencida = abertas["vencimento"] < hoje
    fig = go.Figure()
    for flag, nome, cor in ((False, "A vencer", SERIES[0]), (True, "Vencida", CRITICAL)):
        sub = abertas[vencida == flag]
        if sub.empty:
            continue
        fig.add_bar(x=sub["vencimento"], y=sub["valor"], name=nome, marker_color=cor,
                    customdata=sub["descricao"], width=86400000 * 0.8,
                    hovertemplate="%{customdata}<br>%{x|%d/%m/%Y}<br>R$ %{y:,.2f}<extra>" + nome + "</extra>")
    fig.add_vline(x=hoje, line=dict(color=MUTED, width=1, dash="dot"))
    fig.update_xaxes(tickformat="%d/%m")
    return _layout(fig, height=300)
