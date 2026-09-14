# %% [markdown]
# # Nível 1 & 2: Análise Macro e Diagnóstico de Tendências Temporais
# **Objetivo:** Identificar anomalias de volumetria e distribuição de variáveis em lote, salvando os gráficos no diretório de assets.

# %%
import glob
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Configuração de Caminhos Absolutos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_DIR = os.path.join(BASE_DIR, "..", "data", "raw")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Configuração visual
sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 5)
plt.rcParams["font.size"] = 10

# %%
raw_files = sorted(glob.glob(os.path.join(DATA_RAW_DIR, "tb_clientes_2025_*.csv")))

if not raw_files:
    raise FileNotFoundError(
        f"Nenhum arquivo CSV encontrado em: {os.path.abspath(DATA_RAW_DIR)}. "
        "Execute 'python src/generate_data.py' primeiro!"
    )

macro_metrics = []
print(" Processando arquivos em lote...")

for file_path in raw_files:
    df_lote = pd.read_csv(file_path)

    mes_ref = df_lote["mes_referencia"].iloc[0]
    total_linhas = len(df_lote)
    cpfs_unicos = df_lote["cpf"].nunique()

    renda_media = df_lote["renda_mensal"].mean()
    renda_mediana = df_lote["renda_mensal"].median()
    renda_std = df_lote["renda_mensal"].std()
    idade_media = df_lote["idade"].mean()

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

df_macro = pd.DataFrame(macro_metrics)
print(" Metadados agregados com sucesso!")

# %% Gráfico A - Volumetria
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

min_idx = df_macro["total_registros"].idxmin()
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
path_grafico_vol = os.path.join(ASSETS_DIR, "grafico_volumetria.png")
plt.savefig(path_grafico_vol, bbox_inches="tight", dpi=300)
plt.close()
print(f" [OK] Gráfico salvo: {path_grafico_vol}")

# %% Gráfico B - Renda
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
plt.yscale("log")
plt.xticks(rotation=45)
plt.legend()

plt.tight_layout()
path_grafico_renda = os.path.join(ASSETS_DIR, "grafico_renda.png")
plt.savefig(path_grafico_renda, bbox_inches="tight", dpi=300)
plt.close()
print(f" [OK] Gráfico salvo: {path_grafico_renda}")