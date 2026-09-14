# %% [markdown]
# # Nível 4: Segregação de Bases, Imputação Lógica e Relatório Final
# **Objetivo:** Aplicar as regras de decisão na base completa para separar os dados em Gold, Silver (Imputados) e Quarentena, exportando as bases em Parquet e gerando a matriz de aproveitamento de dados.

# %%
import glob
import os
import re
import time
import numpy as np
import pandas as pd

# 1. Configuração de Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_DIR = os.path.join(BASE_DIR, "..", "data", "raw")
DATA_PROC_DIR = os.path.join(BASE_DIR, "..", "data", "processed")
os.makedirs(DATA_PROC_DIR, exist_ok=True)


# Função de validação sintática do CPF (Vetorizada para performance na base completa)
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


# %% [markdown]
# ## 1. Carregamento e Tratamento da Base Completa

# %%
print(" Carregando a base de dados completa...")
start_time = time.time()

raw_files = sorted(glob.glob(os.path.join(DATA_RAW_DIR, "tb_clientes_2025_*.csv")))
df_full = pd.concat([pd.read_csv(f) for f in raw_files], ignore_index=True)

total_registros_brutos = len(df_full)
print(f" Total de registros carregados: {total_registros_brutos:,}")

# Validação do CPF
print(" Executando checagem de integridade de CPFs...")
df_full["cpf_valido"] = df_full["cpf"].apply(validar_cpf)

# Ordenação temporal por cliente para regras de janela
df_full = df_full.sort_values(by=["id_cliente", "mes_referencia"])

# %% [markdown]
# ## 2. Recuperação de Dados via Imputação Lógica (Base Silver)

# %%
print(" Aplicando regras de recuperação e imputação temporal...")

# A. Correção da Renda do Mês 08 (Erro de escala x100)
mask_erro_renda = df_full["mes_referencia"] == "2025-08"
df_full.loc[mask_erro_renda, "renda_mensal"] = (
    df_full.loc[mask_erro_renda, "renda_mensal"] / 100
)

# B. Identificação e Correção da Idade Anômala no Mês 11 via Histórico do Cliente
df_full["idade_mediana_historica"] = df_full.groupby("id_cliente")[
    "idade"
].transform("median")

mask_erro_idade = (df_full["mes_referencia"] == "2025-11") & (
    (df_full["idade"] - df_full["idade_mediana_historica"]).abs() > 2
)

# Imputação: substitui a idade corrompida pela mediana histórica do próprio cliente
df_full.loc[mask_erro_idade, "idade"] = df_full.loc[
    mask_erro_idade, "idade_mediana_historica"
]

# Marcação do flag de dados imputados/recuperados
df_full["registro_imputado"] = mask_erro_renda | mask_erro_idade

# %% [markdown]
# ## 3. Segregação e Exportação das Bases (Gold, Imputed, Quarantine)

# %%
print(" Segregando as bases de acordo com as regras de governança...")

# 1. Quarentena: CPFs matematicamente inválidos
df_quarantine = df_full[~df_full["cpf_valido"]].copy()

# Base com CPFs Válidos
df_valid_cpf = df_full[df_full["cpf_valido"]].copy()

# 2. Imputed (Silver): Dados validados porém recuperados via regra temporal
df_imputed = df_valid_cpf[df_valid_cpf["registro_imputado"]].copy()

# 3. Gold: Dados 100% íntegros de origem sem necessidade de intervenção
df_gold = df_valid_cpf[~df_valid_cpf["registro_imputado"]].copy()

# Limpeza de colunas auxiliares antes da exportação
cols_finais = [
    "mes_referencia",
    "id_cliente",
    "nome",
    "cpf",
    "idade",
    "renda_mensal",
    "endereco",
]

path_gold = os.path.join(DATA_PROC_DIR, "base_gold.parquet")
path_imputed = os.path.join(DATA_PROC_DIR, "base_imputed.parquet")
path_quarantine = os.path.join(DATA_PROC_DIR, "base_quarantine.parquet")

df_gold[cols_finais].to_parquet(path_gold, index=False)
df_imputed[cols_finais].to_parquet(path_imputed, index=False)
df_quarantine[cols_finais].to_parquet(path_quarantine, index=False)

tempo_total = time.time() - start_time

print(f" [OK] Base Gold salva ({len(df_gold):,} linhas) -> {path_gold}")
print(
    f" [OK] Base Imputed salva ({len(df_imputed):,} linhas) -> {path_imputed}"
)
print(
    f" [OK] Base Quarantine salva ({len(df_quarantine):,} linhas) -> {path_quarantine}"
)

# %% [markdown]
# ## 4. Relatório Final de Aproveitamento de Dados

# %%
pct_gold = (len(df_gold) / total_registros_brutos) * 100
pct_imputed = (len(df_imputed) / total_registros_brutos) * 100
pct_quarantine = (len(df_quarantine) / total_registros_brutos) * 100
pct_aproveitamento_total = pct_gold + pct_imputed

print("\n" + "=" * 65)
print(" MATRIZ EXECUTIVA DE APROVEITAMENTO DE DADOS (DATA QUALITY)")
print("=" * 65)
print(
    f" Total de Registros Auditados: {total_registros_brutos:,} (100.0%)"
)
print(f"  Base GOLD (Íntegros de Origem): {len(df_gold):,} ({pct_gold:.2f}%)")
print(
    f" 🛠️ Base IMPUTED (Recuperados/Corrigidos): {len(df_imputed):,} ({pct_imputed:.2f}%)"
)
print(
    f" ⛔ Base QUARANTINE (Descartados/Invalidados): {len(df_quarantine):,} ({pct_quarantine:.2f}%)"
)
print("-" * 65)
print(
    f" TAXA DE APROVEITAMENTO TOTAL DA BASE: {pct_aproveitamento_total:.2f}%"
)
print(
    f" ⏱️ Tempo de Processamento Completo e Exportação: {tempo_total:.2f} segundos"
)
print("=" * 65)