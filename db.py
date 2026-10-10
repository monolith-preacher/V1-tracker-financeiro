"""Camada de dados (SQLite) do Finance Tracker."""
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "financas.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    categoria TEXT NOT NULL,
    descricao TEXT,
    valor REAL NOT NULL CHECK (valor > 0)
);

CREATE TABLE IF NOT EXISTS contas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    categoria TEXT NOT NULL,
    valor REAL NOT NULL CHECK (valor > 0),
    vencimento TEXT NOT NULL,
    recorrente INTEGER NOT NULL DEFAULT 0,
    pago INTEGER NOT NULL DEFAULT 0,
    data_pagamento TEXT
);

CREATE TABLE IF NOT EXISTS dividas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    credor TEXT,
    valor_original REAL NOT NULL CHECK (valor_original > 0),
    juros_mensal REAL NOT NULL DEFAULT 0,
    parcela REAL NOT NULL DEFAULT 0,
    data_inicio TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pagamentos_divida (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    divida_id INTEGER NOT NULL REFERENCES dividas(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    valor REAL NOT NULL CHECK (valor > 0)
);

CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    meta REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS movimentos_reserva (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reserva_id INTEGER NOT NULL REFERENCES reservas(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    valor REAL NOT NULL CHECK (valor <> 0),
    descricao TEXT
);
"""

CATEGORIAS_RECEITA = ["Salário", "Freelance", "Investimentos", "Vendas", "Presente", "Outros"]
CATEGORIAS_DESPESA = [
    "Moradia", "Alimentação", "Transporte", "Saúde", "Educação", "Lazer",
    "Assinaturas", "Contas de casa", "Compras", "Impostos", "Dívidas", "Outros",
]


@contextmanager
def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with conectar() as conn:
        conn.executescript(SCHEMA)


def _df(sql, params=()):
    with conectar() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def _exec(sql, params=()):
    with conectar() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def _iso(d):
    return d.isoformat() if isinstance(d, date) else str(d)


# ---------- Transações ----------

def add_transacao(data, tipo, categoria, descricao, valor):
    return _exec(
        "INSERT INTO transacoes (data, tipo, categoria, descricao, valor) VALUES (?,?,?,?,?)",
        (_iso(data), tipo, categoria, descricao, float(valor)),
    )


def listar_transacoes():
    df = _df("SELECT * FROM transacoes ORDER BY data DESC, id DESC")
    df["data"] = pd.to_datetime(df["data"])
    return df


def apagar_transacao(tid):
    _exec("DELETE FROM transacoes WHERE id = ?", (int(tid),))


# ---------- Contas a pagar ----------

def add_conta(descricao, categoria, valor, vencimento, recorrente=False):
    return _exec(
        "INSERT INTO contas (descricao, categoria, valor, vencimento, recorrente) VALUES (?,?,?,?,?)",
        (descricao, categoria, float(valor), _iso(vencimento), int(recorrente)),
    )


def listar_contas():
    df = _df("SELECT * FROM contas ORDER BY pago, vencimento")
    df["vencimento"] = pd.to_datetime(df["vencimento"])
    df["data_pagamento"] = pd.to_datetime(df["data_pagamento"])
    df["pago"] = df["pago"].astype(bool)
    df["recorrente"] = df["recorrente"].astype(bool)
    return df


def _proximo_mes(d):
    ano, mes = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    dia = d.day
    while True:
        try:
            return date(ano, mes, dia)
        except ValueError:
            dia -= 1


def pagar_conta(cid, data_pagamento=None, registrar_despesa=True):
    """Marca a conta como paga; opcionalmente lança a despesa e,
    se recorrente, agenda a do mês seguinte."""
    data_pagamento = data_pagamento or date.today()
    with conectar() as conn:
        row = conn.execute(
            "SELECT descricao, categoria, valor, vencimento, recorrente FROM contas WHERE id = ?",
            (int(cid),),
        ).fetchone()
        if row is None:
            return
        descricao, categoria, valor, vencimento, recorrente = row
        conn.execute(
            "UPDATE contas SET pago = 1, data_pagamento = ? WHERE id = ?",
            (_iso(data_pagamento), int(cid)),
        )
        if registrar_despesa:
            conn.execute(
                "INSERT INTO transacoes (data, tipo, categoria, descricao, valor) VALUES (?,?,?,?,?)",
                (_iso(data_pagamento), "despesa", categoria, descricao, valor),
            )
        if recorrente:
            prox = _proximo_mes(date.fromisoformat(vencimento))
            conn.execute(
                "INSERT INTO contas (descricao, categoria, valor, vencimento, recorrente) VALUES (?,?,?,?,1)",
                (descricao, categoria, valor, prox.isoformat()),
            )


def apagar_conta(cid):
    _exec("DELETE FROM contas WHERE id = ?", (int(cid),))


# ---------- Dívidas ----------

def add_divida(nome, credor, valor_original, juros_mensal, parcela, data_inicio):
    return _exec(
        "INSERT INTO dividas (nome, credor, valor_original, juros_mensal, parcela, data_inicio) "
        "VALUES (?,?,?,?,?,?)",
        (nome, credor, float(valor_original), float(juros_mensal), float(parcela), _iso(data_inicio)),
    )


def listar_dividas():
    df = _df(
        """
        SELECT d.*, COALESCE(SUM(p.valor), 0) AS pago
        FROM dividas d LEFT JOIN pagamentos_divida p ON p.divida_id = d.id
        GROUP BY d.id ORDER BY d.nome
        """
    )
    df["saldo"] = (df["valor_original"] - df["pago"]).clip(lower=0)
    return df


def pagar_divida(divida_id, data, valor, registrar_despesa=True):
    with conectar() as conn:
        conn.execute(
            "INSERT INTO pagamentos_divida (divida_id, data, valor) VALUES (?,?,?)",
            (int(divida_id), _iso(data), float(valor)),
        )
        if registrar_despesa:
            nome = conn.execute("SELECT nome FROM dividas WHERE id = ?", (int(divida_id),)).fetchone()[0]
            conn.execute(
                "INSERT INTO transacoes (data, tipo, categoria, descricao, valor) VALUES (?,?,?,?,?)",
                (_iso(data), "despesa", "Dívidas", "Pagamento: " + nome, float(valor)),
            )


def listar_pagamentos_divida():
    df = _df(
        """
        SELECT p.id, p.divida_id, d.nome, p.data, p.valor
        FROM pagamentos_divida p JOIN dividas d ON d.id = p.divida_id
        ORDER BY p.data
        """
    )
    df["data"] = pd.to_datetime(df["data"])
    return df


def apagar_divida(did):
    _exec("DELETE FROM dividas WHERE id = ?", (int(did),))


# ---------- Reservas (o que estamos guardando) ----------

def add_reserva(nome, meta):
    return _exec("INSERT INTO reservas (nome, meta) VALUES (?,?)", (nome, float(meta)))


def atualizar_meta(rid, meta):
    _exec("UPDATE reservas SET meta = ? WHERE id = ?", (float(meta), int(rid)))


def listar_reservas():
    return _df(
        """
        SELECT r.id, r.nome, r.meta, COALESCE(SUM(m.valor), 0) AS saldo
        FROM reservas r LEFT JOIN movimentos_reserva m ON m.reserva_id = r.id
        GROUP BY r.id ORDER BY r.nome
        """
    )


def movimentar_reserva(reserva_id, data, valor, descricao=""):
    """valor > 0 = aporte, valor < 0 = retirada."""
    _exec(
        "INSERT INTO movimentos_reserva (reserva_id, data, valor, descricao) VALUES (?,?,?,?)",
        (int(reserva_id), _iso(data), float(valor), descricao),
    )


def listar_movimentos_reserva():
    df = _df(
        """
        SELECT m.id, m.reserva_id, r.nome, m.data, m.valor, m.descricao
        FROM movimentos_reserva m JOIN reservas r ON r.id = m.reserva_id
        ORDER BY m.data
        """
    )
    df["data"] = pd.to_datetime(df["data"])
    return df


def apagar_reserva(rid):
    _exec("DELETE FROM reservas WHERE id = ?", (int(rid),))


def apagar_movimento_reserva(mid):
    _exec("DELETE FROM movimentos_reserva WHERE id = ?", (int(mid),))


def banco_vazio():
    with conectar() as conn:
        for tabela in ("transacoes", "contas", "dividas", "reservas"):
            if conn.execute("SELECT 1 FROM " + tabela + " LIMIT 1").fetchone():
                return False
    return True
