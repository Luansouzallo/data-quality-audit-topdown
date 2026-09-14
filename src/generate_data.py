import os
import random
import numpy as np
import pandas as pd
from faker import Faker

# Configuração de sementes para reproducibilidade
fake = Faker("pt_BR")
Faker.seed(42)
np.random.seed(42)
random.seed(42)

OUTPUT_DIR = "data/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_valid_cpf():
    """Gera um CPF matematicamente válido."""
    return fake.cpf()


def generate_invalid_cpf():
    """Gera CPFs com falhas sintáticas ou zerados."""
    options = [
        "000.000.000-00",
        "111.111.111-11",
        "123.456.789-00",  # Dígito verificador inválido
        fake.cpf()[:-2] + "00",
    ]
    return random.choice(options)


# 1. Base fixa de clientes (para manter consistência temporal entre os meses)
NUM_CLIENTS_BASE = 60000
print("Gerando cadastro base de clientes...")

client_pool = []
for i in range(1, NUM_CLIENTS_BASE + 1):
    client_pool.append(
        {
            "id_cliente": f"CLI-{i:06d}",
            "nome": fake.name(),
            "cpf": generate_valid_cpf(),
            "idade_base": random.randint(18, 75),
            "renda_base": round(random.uniform(1500.0, 25000.0), 2),
            "endereco": fake.address().replace("\n", ", "),
        }
    )

df_clients = pd.DataFrame(client_pool)

# 2. Gerar as 12 tabelas mensais injetando anomalias
print("Gerando as 12 tabelas mensais com anomalias...")

for mes in range(1, 13):
    mes_str = f"{mes:02d}"

    # Regra de Volumetria: Mês 06 tem perda severa de linhas (15 mil vs ~50 mil)
    sample_size = 15000 if mes == 6 else 50000

    # Amostra aleatória do pool de clientes para o mês corrente
    df_month = df_clients.sample(n=sample_size, replace=False).copy()
    df_month["mes_referencia"] = f"2025-{mes_str}"

    # Ajuste fino da idade (+1 ano se virou o período) e pequena oscilação natural da renda
    df_month["idade"] = df_month["idade_base"]
    df_month["renda_mensal"] = df_month["renda_base"].apply(
        lambda x: round(x * random.uniform(0.98, 1.02), 2)
    )

    # --- INJEÇÃO DE ANOMALIAS ---

    # Anomalia 1: CPFs Inválidos/Nulos (~3% da base em todos os meses)
    invalid_mask = np.random.rand(len(df_month)) < 0.03
    df_month.loc[invalid_mask, "cpf"] = [
        generate_invalid_cpf() for _ in range(invalid_mask.sum())
    ]

    # Anomalia 2: Erro de Formatação na Renda no Mês 08 (Renda x 100 - Ponto flutuante)
    if mes == 8:
        df_month["renda_mensal"] = df_month["renda_mensal"] * 100

    # Anomalia 3: Incoerência Temporal na Idade no Mês 11 (Salto anômalo de idade)
    if mes == 11:
        age_anomaly_mask = np.random.rand(len(df_month)) < 0.15  # 15% dos registros
        df_month.loc[age_anomaly_mask, "idade"] = df_month.loc[
            age_anomaly_mask, "idade"
        ].apply(lambda x: x + random.choice([20, 30, -15]))

    # Seleção e ordenação final das colunas
    df_month = df_month[
        [
            "mes_referencia",
            "id_cliente",
            "nome",
            "cpf",
            "idade",
            "renda_mensal",
            "endereco",
        ]
    ]

    # Salvar em CSV e Parquet dentro de data/raw/
    file_path_csv = os.path.join(OUTPUT_DIR, f"tb_clientes_2025_{mes_str}.csv")
    df_month.to_csv(file_path_csv, index=False)

    print(
        f" [OK] Tabela Mês {mes_str} gerada: {len(df_month):,} registros -> {file_path_csv}"
    )

print(
    "\nBase de dados sintética criada com sucesso na pasta 'data/raw/'!"
)