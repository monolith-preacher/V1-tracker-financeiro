"""Finance Tracker — rode com:  streamlit run app.py"""
from datetime import date

import pandas as pd
import streamlit as st

import charts as ch
import db
from charts import brl

st.set_page_config(page_title="Finance Tracker", page_icon="💰", layout="wide")
db.init_db()

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        background: #fcfcfb; border: 1px solid rgba(11,11,11,0.10);
        border-radius: 10px; padding: 12px 16px;
    }
    [data-testid="stMetricLabel"] p { color: #52514e; }
    </style>
    """,
    unsafe_allow_html=True,
)


def grafico(fig):
    st.plotly_chart(fig, use_container_width=True, config=ch.CONFIG)


def em_reais(df, *colunas):
    """Formata colunas monetárias como texto em R$ (com separador de milhar)."""
    df = df.copy()
    for c in colunas:
        df[c] = df[c].map(lambda v: "" if pd.isna(v) else brl(v))
    return df


def tabela_com_exclusao(df, colunas, chave, ao_excluir, column_config=None):
    """Mostra uma tabela com coluna 'Excluir' e apaga as linhas marcadas."""
    if df.empty:
        st.caption("Nada cadastrado ainda.")
        return
    moeda = [c for c in ("valor", "valor_original", "saldo") if c in colunas]
    vis = em_reais(df[["id"] + colunas], *moeda)
    vis.insert(0, "Excluir", False)
    editado = st.data_editor(
        vis, key=chave, hide_index=True, use_container_width=True,
        disabled=["id"] + colunas,
        column_config={"id": None, **(column_config or {})},
    )
    marcados = editado[editado["Excluir"]]["id"].tolist()
    if marcados and st.button(f"Excluir {len(marcados)} selecionado(s)", key=chave + "_btn", type="primary"):
        for i in marcados:
            ao_excluir(i)
        st.rerun()


# ======================================================================
# Painel
# ======================================================================
def pagina_painel():
    st.title("Painel financeiro")

    trans = db.listar_transacoes()
    contas = db.listar_contas()
    dividas = db.listar_dividas()
    reservas = db.listar_reservas()
    movs = db.listar_movimentos_reserva()

    periodo = st.segmented_control(
        "Período", ["Este mês", "3 meses", "6 meses", "12 meses", "Tudo"],
        default="12 meses", key="periodo",
    ) or "12 meses"
    hoje = pd.Timestamp.today().normalize()
    inicio_mes = hoje.replace(day=1)
    meses = {"Este mês": 1, "3 meses": 3, "6 meses": 6, "12 meses": 12}.get(periodo)
    if meses:
        inicio = inicio_mes - pd.DateOffset(months=meses - 1)
        t = trans[trans["data"] >= inicio]
    else:
        t = trans

    # ---- Números do mês atual ----
    st.subheader("Mês atual")
    tm = trans[trans["data"] >= inicio_mes]
    rec_mes = tm.loc[tm["tipo"] == "receita", "valor"].sum()
    desp_mes = tm.loc[tm["tipo"] == "despesa", "valor"].sum()
    abertas = contas[~contas["pago"]]
    a_pagar_30 = abertas.loc[abertas["vencimento"] <= hoje + pd.Timedelta(days=30), "valor"].sum()
    vencidas = abertas[abertas["vencimento"] < hoje]

    c = st.columns(4)
    c[0].metric("Renda do mês", brl(rec_mes))
    c[1].metric("Gastos do mês", brl(desp_mes))
    c[2].metric("Sobra do mês", brl(rec_mes - desp_mes),
                delta=f"{(rec_mes - desp_mes) / rec_mes:.0%} da renda" if rec_mes else None)
    c[3].metric("A pagar (30 dias)", brl(a_pagar_30),
                delta=f"{len(vencidas)} vencida(s)" if len(vencidas) else None, delta_color="inverse")

    st.subheader("Patrimônio")
    total_guardado = reservas["saldo"].sum()
    total_divida = dividas["saldo"].sum()
    parcelas = dividas.loc[dividas["saldo"] > 0, "parcela"].sum()
    c = st.columns(4)
    c[0].metric("Total guardado", brl(total_guardado))
    c[1].metric("Total em dívidas", brl(total_divida))
    c[2].metric("Patrimônio líquido", brl(total_guardado - total_divida))
    c[3].metric("Parcelas de dívida / mês", brl(parcelas))

    # ---- Gráficos ----
    st.divider()
    st.subheader(f"Receitas × despesas por mês — {periodo.lower()}")
    grafico(ch.receitas_vs_despesas(t))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Para onde vai o dinheiro** (despesas por categoria)")
        grafico(ch.despesas_por_categoria(t))
    with col2:
        st.markdown("**De onde vem o dinheiro** (receitas por categoria)")
        grafico(ch.receitas_por_categoria(t))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**O que estamos guardando** (saldo vs. meta por área)")
        grafico(ch.reservas_progresso(reservas))
    with col2:
        st.markdown("**Dívidas** (pago vs. falta pagar)")
        grafico(ch.dividas_saldo(dividas))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Contas a pagar** (em aberto por vencimento)")
        grafico(ch.contas_proximas(contas))
    with col2:
        st.markdown("**Evolução das reservas**")
        grafico(ch.evolucao_reservas(movs, reservas))

    # ---- Tabela-resumo em números ----
    st.divider()
    st.subheader("Resumo mensal em números")
    m = ch.resumo_mensal(t)
    if m.empty:
        st.caption("Sem transações no período.")
    else:
        m = m.sort_values("mes", ascending=False)
        m["taxa_poupanca"] = (m["saldo"] / m["receita"].where(m["receita"] > 0)).fillna(0) * 100
        st.dataframe(
            em_reais(m, "receita", "despesa", "saldo"), hide_index=True, use_container_width=True,
            column_config={
                "mes": st.column_config.DateColumn("Mês", format="MM/YYYY"),
                "receita": "Receitas", "despesa": "Despesas", "saldo": "Saldo",
                "taxa_poupanca": st.column_config.ProgressColumn(
                    "% da renda que sobrou", format="%.0f%%", min_value=0, max_value=100),
            },
        )


# ======================================================================
# Transações (renda e gastos)
# ======================================================================
def pagina_transacoes():
    st.title("Receitas e despesas")

    with st.form("nova_transacao", clear_on_submit=True, border=True):
        st.markdown("**Novo lançamento**")
        c = st.columns([1, 1, 1.4, 2, 1])
        tipo = c[0].selectbox("Tipo", ["despesa", "receita"], format_func=str.capitalize)
        data = c[1].date_input("Data", value=date.today(), format="DD/MM/YYYY")
        categoria = c[2].selectbox("Categoria", db.CATEGORIAS_DESPESA + [x for x in db.CATEGORIAS_RECEITA
                                                                         if x not in db.CATEGORIAS_DESPESA])
        descricao = c[3].text_input("Descrição")
        valor = c[4].number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f")
        if st.form_submit_button("Adicionar", type="primary"):
            if valor <= 0:
                st.error("Informe um valor maior que zero.")
            else:
                db.add_transacao(data, tipo, categoria, descricao, valor)
                st.success("Lançamento adicionado.")
                st.rerun()

    trans = db.listar_transacoes()
    if trans.empty:
        st.info("Nenhum lançamento ainda.")
        return

    c = st.columns(3)
    tipos = c[0].multiselect("Tipo", ["receita", "despesa"], default=["receita", "despesa"])
    cats = c[1].multiselect("Categorias", sorted(trans["categoria"].unique()))
    min_d, max_d = trans["data"].min().date(), trans["data"].max().date()
    intervalo = c[2].date_input("Intervalo", value=(min_d, max_d), format="DD/MM/YYYY")

    f = trans[trans["tipo"].isin(tipos)]
    if cats:
        f = f[f["categoria"].isin(cats)]
    if isinstance(intervalo, tuple) and len(intervalo) == 2:
        f = f[(f["data"].dt.date >= intervalo[0]) & (f["data"].dt.date <= intervalo[1])]

    rec = f.loc[f["tipo"] == "receita", "valor"].sum()
    desp = f.loc[f["tipo"] == "despesa", "valor"].sum()
    c = st.columns(4)
    c[0].metric("Receitas", brl(rec))
    c[1].metric("Despesas", brl(desp))
    c[2].metric("Saldo", brl(rec - desp))
    c[3].metric("Lançamentos", len(f))

    st.markdown("**Saldo acumulado no período**")
    grafico(ch.saldo_acumulado(f))

    tabela_com_exclusao(
        f, ["data", "tipo", "categoria", "descricao", "valor"], "tab_trans", db.apagar_transacao,
        {"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
         "tipo": "Tipo", "categoria": "Categoria", "descricao": "Descrição",
         "valor": "Valor"},
    )


# ======================================================================
# Contas a pagar
# ======================================================================
def pagina_contas():
    st.title("Contas a pagar")

    with st.form("nova_conta", clear_on_submit=True):
        st.markdown("**Nova conta**")
        c = st.columns([2, 1.4, 1, 1, 1])
        descricao = c[0].text_input("Descrição")
        categoria = c[1].selectbox("Categoria", db.CATEGORIAS_DESPESA)
        valor = c[2].number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f")
        venc = c[3].date_input("Vencimento", value=date.today(), format="DD/MM/YYYY")
        rec = c[4].checkbox("Repete todo mês", value=False)
        if st.form_submit_button("Adicionar", type="primary"):
            if not descricao or valor <= 0:
                st.error("Preencha a descrição e um valor maior que zero.")
            else:
                db.add_conta(descricao, categoria, valor, venc, rec)
                st.rerun()

    contas = db.listar_contas()
    hoje = pd.Timestamp.today().normalize()
    abertas = contas[~contas["pago"]]
    vencidas = abertas[abertas["vencimento"] < hoje]
    prox7 = abertas[(abertas["vencimento"] >= hoje) & (abertas["vencimento"] <= hoje + pd.Timedelta(days=7))]

    c = st.columns(4)
    c[0].metric("Total em aberto", brl(abertas["valor"].sum()), f"{len(abertas)} conta(s)", delta_color="off")
    c[1].metric("Vencidas", brl(vencidas["valor"].sum()),
                f"{len(vencidas)} conta(s)" if len(vencidas) else None, delta_color="inverse")
    c[2].metric("Próximos 7 dias", brl(prox7["valor"].sum()))
    c[3].metric("Pago este mês",
                brl(contas.loc[contas["pago"] & (contas["data_pagamento"] >= hoje.replace(day=1)), "valor"].sum()))

    grafico(ch.contas_proximas(contas))

    st.subheader("Em aberto")
    if abertas.empty:
        st.caption("Tudo pago! 🎉")
    registrar = st.checkbox("Ao pagar, lançar também como despesa", value=True)
    for r in abertas.itertuples():
        atraso = r.vencimento < hoje
        c = st.columns([3, 1.2, 1.2, 1, 1])
        c[0].markdown(f"**{r.descricao}** · {r.categoria}" + (" · 🔁 mensal" if r.recorrente else ""))
        c[1].markdown(brl(r.valor))
        c[2].markdown(("⚠️ **Vencida** " if atraso else "") + r.vencimento.strftime("%d/%m/%Y"))
        if c[3].button("Paguei", key=f"pagar_{r.id}"):
            db.pagar_conta(r.id, registrar_despesa=registrar)
            st.rerun()
        if c[4].button("Excluir", key=f"del_conta_{r.id}"):
            db.apagar_conta(r.id)
            st.rerun()

    st.subheader("Histórico de pagas")
    pagas = contas[contas["pago"]].sort_values("data_pagamento", ascending=False)
    tabela_com_exclusao(
        pagas, ["descricao", "categoria", "valor", "vencimento", "data_pagamento"], "tab_pagas", db.apagar_conta,
        {"descricao": "Descrição", "categoria": "Categoria",
         "valor": "Valor",
         "vencimento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
         "data_pagamento": st.column_config.DateColumn("Pago em", format="DD/MM/YYYY")},
    )


# ======================================================================
# Dívidas
# ======================================================================
def pagina_dividas():
    st.title("Dívidas")

    with st.form("nova_divida", clear_on_submit=True):
        st.markdown("**Nova dívida**")
        c = st.columns([2, 1.4, 1.2, 1, 1, 1])
        nome = c[0].text_input("Nome")
        credor = c[1].text_input("Credor")
        valor = c[2].number_input("Valor total (R$)", min_value=0.0, step=100.0, format="%.2f")
        juros = c[3].number_input("Juros % a.m.", min_value=0.0, step=0.1, format="%.2f")
        parcela = c[4].number_input("Parcela (R$)", min_value=0.0, step=50.0, format="%.2f")
        inicio = c[5].date_input("Início", value=date.today(), format="DD/MM/YYYY")
        if st.form_submit_button("Adicionar", type="primary"):
            if not nome or valor <= 0:
                st.error("Preencha o nome e um valor maior que zero.")
            else:
                db.add_divida(nome, credor, valor, juros, parcela, inicio)
                st.rerun()

    dividas = db.listar_dividas()
    pags = db.listar_pagamentos_divida()

    ativas = dividas[dividas["saldo"] > 0]
    c = st.columns(4)
    c[0].metric("Saldo devedor total", brl(dividas["saldo"].sum()))
    c[1].metric("Já pago", brl(dividas["pago"].sum()))
    c[2].metric("Parcelas por mês", brl(ativas["parcela"].sum()))
    c[3].metric("Dívidas ativas", len(ativas))

    if dividas.empty:
        st.info("Nenhuma dívida cadastrada.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Pago vs. falta pagar**")
        grafico(ch.dividas_saldo(dividas))
    with col2:
        st.markdown("**Saldo devedor total ao longo do tempo**")
        grafico(ch.evolucao_dividas(dividas, pags))

    st.subheader("Detalhes")
    d = dividas.copy()
    d["progresso"] = (d["pago"] / d["valor_original"] * 100).clip(upper=100)
    d["meses_restantes"] = (d["saldo"] / d["parcela"].where(d["parcela"] > 0)).apply(
        lambda x: None if pd.isna(x) else int(-(-x // 1)))
    st.dataframe(
        em_reais(d[["nome", "credor", "valor_original", "pago", "saldo", "juros_mensal", "parcela",
                    "meses_restantes", "progresso"]], "valor_original", "pago", "saldo", "parcela"),
        hide_index=True, use_container_width=True,
        column_config={
            "nome": "Dívida", "credor": "Credor",
            "valor_original": "Valor total", "pago": "Pago", "saldo": "Falta",
            "juros_mensal": st.column_config.NumberColumn("Juros a.m.", format="%.2f%%"),
            "parcela": "Parcela",
            "meses_restantes": st.column_config.NumberColumn("Parcelas restantes (aprox.)"),
            "progresso": st.column_config.ProgressColumn("Quitado", format="%.0f%%", min_value=0, max_value=100),
        },
    )
    if (ativas["juros_mensal"] > 0).any():
        pior = ativas.sort_values("juros_mensal", ascending=False).iloc[0]
        st.caption(f"💡 Maior juros: **{pior['nome']}** ({pior['juros_mensal']:.2f}% a.m.) — "
                   "priorizar amortizar essa costuma economizar mais.")

    st.subheader("Registrar pagamento")
    with st.form("pag_divida", clear_on_submit=True):
        c = st.columns([2, 1, 1, 1.5])
        opcoes = dict(zip(dividas["nome"], dividas["id"]))
        escolha = c[0].selectbox("Dívida", list(opcoes))
        padrao = float(dividas.set_index("nome").loc[escolha, "parcela"]) if escolha else 0.0
        valor = c[1].number_input("Valor (R$)", min_value=0.0, value=padrao, step=50.0, format="%.2f")
        data = c[2].date_input("Data", value=date.today(), format="DD/MM/YYYY")
        lancar = c[3].checkbox("Lançar como despesa", value=True)
        if st.form_submit_button("Registrar", type="primary") and valor > 0:
            db.pagar_divida(opcoes[escolha], data, valor, lancar)
            st.rerun()

    with st.expander("Gerenciar dívidas cadastradas"):
        tabela_com_exclusao(dividas, ["nome", "credor", "valor_original"], "tab_div", db.apagar_divida,
                            {"nome": "Dívida", "credor": "Credor",
                             "valor_original": "Valor total"})


# ======================================================================
# Reservas
# ======================================================================
def pagina_reservas():
    st.title("O que estamos guardando")

    reservas = db.listar_reservas()
    movs = db.listar_movimentos_reserva()

    c = st.columns(4)
    c[0].metric("Total guardado", brl(reservas["saldo"].sum()))
    com_meta = reservas[reservas["meta"] > 0]
    c[1].metric("Soma das metas", brl(com_meta["meta"].sum()))
    if not com_meta.empty:
        c[2].metric("Progresso geral das metas",
                    f"{com_meta['saldo'].clip(upper=com_meta['meta']).sum() / com_meta['meta'].sum():.0%}")
    mes = pd.Timestamp.today().normalize().replace(day=1)
    c[3].metric("Aportado este mês", brl(movs.loc[(movs["data"] >= mes) & (movs["valor"] > 0), "valor"].sum()))

    col1, col2 = st.columns([1, 2])
    with col1:
        with st.form("nova_reserva", clear_on_submit=True):
            st.markdown("**Nova área**")
            nome = st.text_input("Nome (ex.: Emergência, Viagem, Investimentos)")
            meta = st.number_input("Meta (R$, 0 = sem meta)", min_value=0.0, step=500.0, format="%.2f")
            if st.form_submit_button("Criar", type="primary") and nome:
                if nome in set(reservas["nome"]):
                    st.error("Já existe uma área com esse nome.")
                else:
                    db.add_reserva(nome, meta)
                    st.rerun()
    with col2:
        if reservas.empty:
            st.info("Crie uma área para começar a guardar.")
        else:
            with st.form("mov_reserva", clear_on_submit=True):
                st.markdown("**Guardar / retirar dinheiro**")
                c = st.columns([2, 1, 1, 1])
                opcoes = dict(zip(reservas["nome"], reservas["id"]))
                escolha = c[0].selectbox("Área", list(opcoes))
                operacao = c[1].radio("Operação", ["Guardar", "Retirar"], horizontal=True)
                valor = c[2].number_input("Valor (R$)", min_value=0.0, step=50.0, format="%.2f")
                data = c[3].date_input("Data", value=date.today(), format="DD/MM/YYYY")
                desc = st.text_input("Descrição (opcional)")
                if st.form_submit_button("Confirmar", type="primary") and valor > 0:
                    db.movimentar_reserva(opcoes[escolha], data, valor if operacao == "Guardar" else -valor, desc)
                    st.rerun()

    if reservas.empty:
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Saldo vs. meta por área**")
        grafico(ch.reservas_progresso(reservas))
    with col2:
        st.markdown("**Evolução do que foi guardado**")
        grafico(ch.evolucao_reservas(movs, reservas))

    st.subheader("Áreas")
    r = reservas.copy()
    r["falta"] = (r["meta"] - r["saldo"]).clip(lower=0)
    r["progresso"] = (r["saldo"] / r["meta"].where(r["meta"] > 0) * 100).clip(upper=100)
    editado = st.data_editor(
        em_reais(r[["id", "nome", "saldo", "meta", "falta", "progresso"]], "saldo", "falta"), hide_index=True, use_container_width=True,
        key="tab_reservas", disabled=["nome", "saldo", "falta", "progresso"],
        column_config={
            "id": None, "nome": "Área",
            "saldo": "Guardado",
            "meta": st.column_config.NumberColumn("Meta (editável)", format="R$ %.2f", min_value=0),
            "falta": "Falta",
            "progresso": st.column_config.ProgressColumn("Progresso", format="%.0f%%", min_value=0, max_value=100),
        },
    )
    mudou = editado[editado["meta"] != r["meta"]]
    if not mudou.empty:
        for row in mudou.itertuples():
            db.atualizar_meta(row.id, row.meta)
        st.rerun()

    with st.expander("Movimentações"):
        tabela_com_exclusao(
            movs.sort_values("data", ascending=False), ["data", "nome", "valor", "descricao"], "tab_movs",
            db.apagar_movimento_reserva,
            {"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "nome": "Área",
             "valor": "Valor", "descricao": "Descrição"},
        )
    with st.expander("Excluir áreas"):
        tabela_com_exclusao(reservas, ["nome", "saldo"], "tab_res_del", db.apagar_reserva,
                            {"nome": "Área", "saldo": "Saldo"})


# ======================================================================
# Navegação
# ======================================================================
with st.sidebar:
    st.markdown("### 💰 Finance Tracker")
    if db.banco_vazio():
        st.info("O banco está vazio.")
        if st.button("Carregar dados de exemplo"):
            import seed
            seed.popular()
            st.rerun()

nav = st.navigation([
    st.Page(pagina_painel, title="Painel", icon="📊", default=True),
    st.Page(pagina_transacoes, title="Receitas e despesas", icon="💸", url_path="transacoes"),
    st.Page(pagina_contas, title="Contas a pagar", icon="🧾", url_path="contas"),
    st.Page(pagina_dividas, title="Dívidas", icon="📉", url_path="dividas"),
    st.Page(pagina_reservas, title="Reservas", icon="🏦", url_path="reservas"),
])
nav.run()
