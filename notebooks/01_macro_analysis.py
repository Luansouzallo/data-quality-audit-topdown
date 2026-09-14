# %% [markdown]
# # Nível 1 & 2: Análise Macro e Diagnóstico de Tendências Temporais
# **Objetivo:** Identificar anomalias de volumetria, distribuição de variáveis e completude de dados nas 12 tabelas mensais antes de descer para a validação registro a registro.

# %%
import glob
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Configuração visual dos gráficos
sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 5)
plt.rcParams["font.size"] = 10

# %% [markdown]
# ## 1. Carregamento por Lotes e Consolidação das Métricas Macro

# %%
# Caminho dos arquivos gerados em data/raw/
# Garante que o caminho seja localizado independente de onde você roda o comando no terminal
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data", "raw")

raw_files = sorted(glob.glob(os.path.join(DATA_DIR, "tb_clientes_2025_*.csv")))

# Validação para evitar rodar o script sem os arquivos gerados
if not raw_files:
    raise FileNotFoundError(
        f"Nenhum arquivo encontrado na pasta: {os.path.abspath(DATA_DIR)}. "
        "Execute primeiro o script 'python src/generate_data.py' para criar as tabelas!"
    )

macro_metrics = []

print(" Processando arquivos em lote...")

for file_path in raw_files:
    # Leitura otimizada por arquivo (lote)
    df_lote = pd.read_csv(file_path)

    mes_ref = df_lote["mes_referencia"].iloc[0]
    total_linhas = len(df_lote)
    cpfs_unicos = df_lote["cpf"].nunique()

    # Métricas agregadas da Renda Mensal
    renda_media = df_lote["renda_mensal"].mean()
    renda_mediana = df_lote["renda_mensal"].median()
    renda_std = df_lote["renda_mensal"].std()

    # Métricas agregadas da Idade
    idade_media = df_lote["idade"].mean()

    # Percentual de Nulos por coluna
    nulos_pct = (df_lote.isnull().sum() / total_linhas * 100).to_dict()

    macro_metrics.append(
        {
            "mes_referencia": mes_ref,
            "total_registros": total_linhas,
            "cpfs_unicos": cpfs_unicos,
            "renda_media": renda_media,
            "renda_mediana": renda_mediana,
            "renda_std": renda_std,
            "idade_media": idade_media,
            "pct_nulos_cpf": nulos_pct.get("cpf", 0),
            "pct_nulos_renda": nulos_pct.get("renda_mensal", 0),
        }
    )

# Consolidação em um DataFrame de Metadados Macro
df_macro = pd.DataFrame(macro_metrics)
print(" Metadados agregados com sucesso!")
df_macro

# %% [markdown]
# ## 2. Visualização das Anomalias Encontradas

# %% [markdown]
# ### A. Anomalia de Volumetria (Nível 1 - Diagnóstico da Ingestão)
# *Identifica se houve perda maciça de registros em algum mês da série temporal.*

# %%
plt.figure(figsize=(12, 4))
ax = sns.lineplot(
    data=df_macro,
    x="mes_referencia",
    y="total_registros",
    marker="o",
    color="#1f77b4",
    linewidth=2.5,
)
plt.title(
    "Volumetria Mensal de Registros - Detecção de Queda na Ingestão (Mês 06)",
    fontsize=12,
    fontweight="bold",
)
plt.xlabel("Mês de Referência")
plt.ylabel("Total de Linhas")
plt.xticks(rotation=45)

# Destaque do ponto anômalo (Mês 06)
min_idx = df_macro["total_registros"].idxmin()
min_mes = df_macro.loc[min_idx, "mes_referencia"]
min_val = df_macro.loc[min_idx, "total_registros"]

ax.annotate(
    f"Anomalia: Queda severa ({min_val:,} linhas)",
    xy=(min_idx, min_val),
    xytext=(min_idx - 0.5, min_val + 10000),
    arrowprops=dict(facecolor="red", shrink=0.05, width=2, headwidth=8),
    fontweight="bold",
    color="red",
)

plt.tight_layout()
plt.show()

# %% [markdown]
# ### B. Anomalia de Distribuição de Renda (Nível 2 - Formatação/Ponto Flutuante)
# *Identifica distorções em métricas financeiras causadas por erro de escala ou conversão.*

# %%
plt.figure(figsize=(12, 4))
plt.plot(
    df_macro["mes_referencia"],
    df_macro["renda_media"],
    marker="o",
    label="Renda Média",
    color="#d62728",
    linewidth=2,
)
plt.plot(
    df_macro["mes_referencia"],
    df_macro["renda_mediana"],
    marker="s",
    label="Renda Mediana",
    color="#2ca02c",
    linewidth=2,
    linestyle="--",
)

plt.title(
    "Comportamento Temporal da Renda Mensal - Erro de Escala/Multiplicação (Mês 08)",
    fontsize=12,
    fontweight="bold",
)
plt.xlabel("Mês de Referência")
plt.ylabel("Valor em R$")
plt.yscale("log")  # Escala logarítmica para evidenciar o salto de ordem de grandeza
plt.xticks(rotation=45)
plt.legend()

plt.tight_layout()
plt.show()

# %% [markdown]
# ### C. Resumo dos Achados Macro para o Relatório de Governança

# %%
print("=" * 60)
print(" DIAGNÓSTICO DA ANÁLISE MACRO (TOP-DOWN)")
print("=" * 60)

# Diagnóstico Mês 06
vol_media = df_macro[df_macro["mes_referencia"] != "2025-06"][
    "total_registros"
].mean()
vol_m6 = df_macro[df_macro["mes_referencia"] == "2025-06"][
    "total_registros"
].values[0]
pct_queda = ((vol_media - vol_m6) / vol_media) * 100

print(
    f"1. Falha de Ingestão (Mês 2025-06): Queda de {pct_queda:.1f}% no volume de dados em relação à média habitual."
)

# Diagnóstico Mês 08
renda_m7 = df_macro[df_macro["mes_referencia"] == "2025-07"][
    "renda_media"
].values[0]
renda_m8 = df_macro[df_macro["mes_referencia"] == "2025-08"][
    "renda_media"
].values[0]
fator_multiplicador = renda_m8 / renda_m7

print(
    f"2. Erro de Formatação (Mês 2025-08): A renda média saltou {fator_multiplicador:.0f}x, indicando erro de conversão/ponto flutuante."
)
print("=" * 60)