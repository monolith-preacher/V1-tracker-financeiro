# 💰 Finance Tracker

Aplicativo web simples para controle de finanças pessoais, feito em **Python** com **Streamlit**, **Plotly** e **SQLite**. Ele roda localmente no seu computador, e os dados ficam salvos num arquivo de banco de dados (`financas.db`) na pasta do projeto. Nada é enviado para a internet.

## O que ele faz

O app é dividido em cinco páginas, acessíveis pelo menu lateral:

| Página | Para que serve |
| --- | --- |
| 📊 **Painel** | Visão geral: renda, gastos e sobra do mês, contas a pagar nos próximos 30 dias, patrimônio líquido (reservas − dívidas) e gráficos de receitas × despesas, gastos por categoria, progresso das reservas, dívidas e evolução do patrimônio. Dá para filtrar por período (mês atual, 3, 6, 12 meses ou tudo). |
| 💸 **Receitas e despesas** | Lançamento das entradas e saídas de dinheiro, separadas por categoria (Salário, Moradia, Alimentação, Lazer etc.). |
| 🧾 **Contas a pagar** | Cadastro de contas com vencimento. Ao marcar uma conta como paga, ela pode virar uma despesa automaticamente; se for recorrente, a do mês seguinte já é agendada. |
| 📉 **Dívidas** | Controle de financiamentos, empréstimos e cartão: valor total, juros, parcela, quanto já foi pago e quanto falta. |
| 🏦 **Reservas** | "Caixinhas" de dinheiro guardado (reserva de emergência, viagem, investimentos…) com meta, aportes e retiradas. |

Os valores são exibidos no formato brasileiro (R$ 1.234,56).

## Como executar

### Pré-requisitos

- Python 3.10 ou superior
- `pip`

### Passo a passo

1. **Entre na pasta do projeto:**

   ```bash
   cd tracker_financeiro
   ```

2. **Crie e ative um ambiente virtual** (recomendado):

   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Linux / macOS
   # venv\Scripts\activate         # Windows
   ```

3. **Instale as dependências:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Rode o app:**

   ```bash
   streamlit run app.py
   ```

   O navegador abre sozinho em `http://localhost:8501`. Se não abrir, acesse esse endereço manualmente.

Para encerrar, pressione `Ctrl + C` no terminal.

### Dados de exemplo

Na primeira execução o banco está vazio. Para explorar o app antes de cadastrar seus próprios dados, clique em **"Carregar dados de exemplo"** no menu lateral. Isso gera 12 meses fictícios de receitas, despesas, contas, dívidas e reservas.

Para começar do zero de novo, basta apagar o arquivo `financas.db` e reiniciar o app.

## Estrutura do projeto

```
tracker_financeiro/
├── app.py            # Interface (páginas do Streamlit)
├── charts.py         # Gráficos com Plotly e formatação em R$
├── db.py             # Acesso ao banco SQLite (tabelas e consultas)
├── seed.py           # Gerador de dados de exemplo
├── requirements.txt  # Dependências
└── financas.db       # Banco de dados (criado automaticamente, fora do git)
```

## Observações

- O arquivo `financas.db` está no `.gitignore`, então seus dados financeiros não vão para o repositório.
- Faça backup copiando o `financas.db` para outro lugar de vez em quando.
