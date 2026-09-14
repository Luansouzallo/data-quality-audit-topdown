# %% [markdown]
# # Nível 3: Amostragem Estatística e Validação Micro
# **Objetivo:** Executar amostragem estatística e aplicar algoritmo real de verificação de CPF e coerência temporal.

# %%
import glob
import os
import re
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_DIR = os.path.join(BASE_DIR, "..", "data", "raw")
DATA_PROC_DIR = os.path.join(BASE_DIR, "..", "data", "processed")
os.makedirs(DATA_PROC_DIR, exist_ok=True)


def validar_cpf(cpf_str: str) -> bool:
    if not isinstance(cpf_str, str):
        return False
    cpf = re.sub(r"\D", "", cpf_str)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    d1 = 0 if resto == 10 else resto
    if int(cpf[9]) != d1:
        return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    d2 = 0 if resto == 10 else resto
    return int(cpf[10]) == d2


raw_files = sorted(glob.glob(os.path.join(DATA_RAW_DIR, "tb_clientes_2025_*.csv")))
dfs_amostrados = []
dfs_completos = []

SAMPLE_SIZE_PER_MONTH = 1200
print(" Aplicando Amostragem Estratificada...")

for file_path in raw_files:
    df_lote = pd.read_csv(file_path)
    dfs_completos.append(df_lote)

    tam_amostra = min(SAMPLE_SIZE_PER_MONTH, len(df_lote))
    df_amostra = df_lote.sample(n=tam_amostra, random_state=42).copy()
    dfs_amostrados.append(df_amostra)

df_full = pd.concat(dfs_completos, ignore_index=True)
df_sample = pd.concat(dfs_amostrados, ignore_index=True)

print(" Executando Validações Micro na Amostra...")
df_sample["cpf_valido"] = df_sample["cpf"].apply(validar_cpf)

df_sample = df_sample.sort_values(by=["id_cliente", "mes_referencia"])
df_sample["idade_anterior"] = df_sample.groupby("id_cliente")["idade"].shift(1)
df_sample["renda_anterior"] = df_sample.groupby("id_cliente")[
    "renda_mensal"
].shift(1)

df_sample["delta_idade"] = (
    df_sample["idade"] - df_sample["idade_anterior"]
).abs()
df_sample["erro_idade_temporal"] = df_sample["delta_idade"] > 2

df_sample["razao_renda"] = (
    df_sample["renda_mensal"] / df_sample["renda_anterior"]
)
df_sample["erro_renda_escala"] = (df_sample["razao_renda"] > 10) | (
    df_sample["razao_renda"] < 0.1
)

output_path = os.path.join(DATA_PROC_DIR, "audit_sample_results.csv")
df_sample.to_csv(output_path, index=False)
print(f" [OK] Amostra auditada salva em: {output_path}")