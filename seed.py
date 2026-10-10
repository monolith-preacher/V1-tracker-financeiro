"""Gera dados de exemplo (últimos 12 meses) para explorar o app."""
import random
from datetime import date, timedelta

import db


def _mes_atras(n):
    hoje = date.today()
    ano, mes = hoje.year, hoje.month - n
    while mes <= 0:
        mes += 12
        ano -= 1
    return ano, mes


def popular():
    rnd = random.Random(42)
    hoje = date.today()

    for n in range(11, -1, -1):
        ano, mes = _mes_atras(n)
        d = lambda dia: min(date(ano, mes, dia), hoje)  # noqa: E731
        db.add_transacao(d(5), "receita", "Salário", "Salário", 6500)
        if rnd.random() < 0.5:
            db.add_transacao(d(18), "receita", "Freelance", "Projeto freelance", rnd.randint(600, 2200))
        db.add_transacao(d(10), "despesa", "Moradia", "Aluguel", 1800)
        db.add_transacao(d(12), "despesa", "Contas de casa", "Luz + água + internet", rnd.randint(280, 420))
        db.add_transacao(d(15), "despesa", "Alimentação", "Mercado", rnd.randint(900, 1300))
        db.add_transacao(d(20), "despesa", "Transporte", "Combustível / app", rnd.randint(250, 500))
        db.add_transacao(d(8), "despesa", "Assinaturas", "Streaming + academia", 160)
        db.add_transacao(d(22), "despesa", "Lazer", "Saídas", rnd.randint(200, 700))
        if rnd.random() < 0.3:
            db.add_transacao(d(25), "despesa", "Saúde", "Farmácia / consulta", rnd.randint(100, 450))

    # Reservas
    areas = [("Reserva de emergência", 20000, 400), ("Viagem", 8000, 250),
             ("Investimentos", 0, 600), ("Carro novo", 30000, 300)]
    for nome, meta, aporte in areas:
        rid = db.add_reserva(nome, meta)
        db.movimentar_reserva(rid, date(*_mes_atras(12), 1), aporte * 6, "Saldo inicial")
        for n in range(11, -1, -1):
            db.movimentar_reserva(rid, date(*_mes_atras(n), 6), aporte + rnd.randint(-50, 150), "Aporte mensal")
    db.movimentar_reserva(2, date(*_mes_atras(3), 14), -900, "Passagens")

    # Dívidas
    d1 = db.add_divida("Financiamento do carro", "Banco X", 24000, 1.4, 980, date(*_mes_atras(10), 1))
    d2 = db.add_divida("Cartão de crédito", "Banco Y", 3500, 12.5, 700, date(*_mes_atras(4), 1))
    d3 = db.add_divida("Empréstimo pessoal", "Fintech Z", 6000, 2.9, 550, date(*_mes_atras(7), 1))
    for did, parcela, meses in ((d1, 980, 10), (d2, 700, 4), (d3, 550, 7)):
        for n in range(meses - 1, -1, -1):
            db.pagar_divida(did, date(*_mes_atras(n), 10), parcela, registrar_despesa=False)

    # Contas a pagar
    db.add_conta("Aluguel", "Moradia", 1800, hoje + timedelta(days=4), recorrente=True)
    db.add_conta("Internet", "Contas de casa", 120, hoje + timedelta(days=9), recorrente=True)
    db.add_conta("IPVA (parcela)", "Impostos", 640, hoje + timedelta(days=16))
    db.add_conta("Seguro do carro", "Transporte", 310, hoje + timedelta(days=23), recorrente=True)
    db.add_conta("Conta de luz", "Contas de casa", 210, hoje - timedelta(days=2), recorrente=True)
