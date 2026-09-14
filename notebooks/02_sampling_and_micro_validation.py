# %% [markdown]
# # Nível 3: Amostragem Estatística e Validação Micro
# **Objetivo:** Aplicar amostragem estratificada para otimizar tempo/recursos e executar regras finas de validação (algoritmo do CPF e coerência temporal de idade e renda).

# %%
import glob
import os
import re
import numpy as np
import pandas as pd

# 1. Configuração de Diretórios com Caminhos Absolutos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_DIR = os.path.join(BASE_DIR, "..", "data", "raw")
DATA_PROC_DIR = os.path.join(BASE_DIR, "..", "data", "processed")
os.makedirs(DATA_PROC_DIR, exist_ok=True)

# %% [markdown]
# ## 1. Funções de Validação Sintática (Micro Validation)


# %%
def validar_cpf(cpf_str: str) -> bool:
    """Aplica o algoritmo matemático oficial de verificação dos dois dígitos do CPF."""
    if not isinstance(cpf_str, str):
        return False

    # Remove pontuações
    cpf = re.sub(r"\D", "", cpf_str)

    # CPF deve ter 11 dígitos e não ter todos os números iguais (ex: 00000000000)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    # Validação do Primeiro Dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    digito_1 = 0 if resto == 10 else resto

    if int(cpf[9]) != digito_1:
        return False

    # Validação do Segundo Dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    digito_2 = 0 if resto == 10 else resto

    return int(cpf[10]) == digito_2


# Teste rápido das validações
print("--- Teste de Unidade do Algoritmo de CPF ---")
print("CPF 000.000.000-00 é válido?:", validar_cpf("000.000.000-00"))  # Esperado: False
print("CPF com tamanho errado?:", validar_cpf("123.456.789"))  # Esperado: False

# %% [markdown]
# ## 2. Carregamento e Amostragem Estatística Estratificada por Mês

# %%
raw_files = sorted(glob.glob(os.path.join(DATA_RAW_DIR, "tb_clientes_2025_*.csv")))

dfs_amostrados = []
dfs_completos = []

# Nível de confiança ~95% e margem de erro pequena -> ~1.000 a 1.500 amostras por lote
SAMPLE_SIZE_PER_MONTH = 1200

print("\n Aplicando Amostragem Estratificada por Mês...")

for file_path in raw_files:
    df_lote = pd.read_csv(file_path)
    dfs_completos.append(df_lote)

    # Extrai amostra aleatória representativa de cada mês
    tam_amostra = min(SAMPLE_SIZE_PER_MONTH, len(df_lote))
    df_amostra = df_lote.sample(n=tam_amostra, random_state=42).copy()
    dfs_amostrados.append(df_amostra)

# Unifica a base completa e a base amostrada
df_full = pd.concat(dfs_completos, ignore_index=True)
df_sample = pd.concat(dfs_amostrados, ignore_index=True)

print(f"Total de registros na base completa: {len(df_full):,}")
print(
    f"Total de registros na Amostra Processada: {len(df_sample):,} (Redução de {100 - (len(df_sample)/len(df_full)*100):.1f}% do volume)"
)

# %% [markdown]
# ## 3. Aplicação das Regras Micro na Amostra

# %%
print("\n Executando Validação Sintática de CPFs...")
# 1. Validação de CPF
df_sample["cpf_valido"] = df_sample["cpf"].apply(validar_cpf)
taxa_cpf_invalido = (1 - df_sample["cpf_valido"].mean()) * 100
print(f" Taxa global de CPFs inválidos detectada: {taxa_cpf_invalido:.2f}%")

# 2. Identificação de Incoerência Temporal (Análise por Cliente/CPF)
print("\n Auditando Coerência Temporal por ID de Cliente...")
df_sample = df_sample.sort_values(by=["id_cliente", "mes_referencia"])

# Agrupa por ID para calcular variação de idade e variação de renda em relação ao mês anterior
df_sample["idade_anterior"] = df_sample.groupby("id_cliente")["idade"].shift(1)
df_sample["renda_anterior"] = df_sample.groupby("id_cliente")[
    "renda_mensal"
].shift(1)

# Regra Temporal 1: A idade não pode variar abruptamente (ex: salto > 2 anos em meses seguidos)
df_sample["delta_idade"] = (
    df_sample["idade"] - df_sample["idade_anterior"]
).abs()
df_sample["erro_idade_temporal"] = df_sample["delta_idade"] > 2

# Regra Temporal 2: A renda não pode saltar desproporcionalmente (> 10x de um mês para o outro)
df_sample["razao_renda"] = (
    df_sample["renda_mensal"] / df_sample["renda_anterior"]
)
df_sample["erro_renda_escala"] = (df_sample["razao_renda"] > 10) | (
    df_sample["razao_renda"] < 0.1
)

# %% [markdown]
# ## 4. Resumo de Inconsistências Detectadas por Mês

# %%
resumo_micro = (
    df_sample.groupby("mes_referencia")
    .agg(
        total_amostra=("id_cliente", "count"),
        cpfs_invalidos=("cpf_valido", lambda x: (~x).sum()),
        erros_idade=("erro_idade_temporal", "sum"),
        erros_renda_escala=("erro_renda_escala", "sum"),
    )
    .reset_index()
)

print("\n" + "=" * 65)
print(" MATRIZ DE INCONSISTÊNCIAS MICRO (AMOSTRA)")
print("=" * 65)
print(resumo_micro.to_string(index=False))

# Salva resultado intermediário para o próximo notebook (Nível 4)
output_path = os.path.join(DATA_PROC_DIR, "audit_sample_results.csv")
df_sample.to_csv(output_path, index=False)
print(f"\n Resultados salvos com sucesso em: {output_path}")