# %% [markdown]
# # Nível 4: Segregação de Bases e Exportação Automática de Relatórios
# **Objetivo:** Exportar bases Parquet (Gold, Silver, Quarantine) e salvar relatórios de métricas em Markdown e JSON.

# %%
import glob
import json
import os
import re
import time
import numpy as np
import pandas as pd

# Configuração de Caminhos Absolutos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_DIR = os.path.join(BASE_DIR, "..", "data", "raw")
DATA_PROC_DIR = os.path.join(BASE_DIR, "..", "data", "processed")
os.makedirs(DATA_PROC_DIR, exist_ok=True)


def validar_cpf(cpf_str: str) -> bool:
    """Valida o dígito verificador e estrutura matemática do CPF."""
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


print(" Carregando a base de dados completa...")
start_time = time.time()

raw_files = sorted(
    glob.glob(os.path.join(DATA_RAW_DIR, "tb_clientes_2025_*.csv"))
)

if not raw_files:
    raise FileNotFoundError(
        f"Nenhum arquivo CSV encontrado em: {os.path.abspath(DATA_RAW_DIR)}"
    )

df_full = pd.concat([pd.read_csv(f) for f in raw_files], ignore_index=True)
total_registros_brutos = len(df_full)
print(f" Total de registros carregados: {total_registros_brutos:,}")

# %% Validação de CPFs e Correção Temporal
print(" Executando checagem de integridade de CPFs...")
df_full["cpf_valido"] = df_full["cpf"].apply(validar_cpf)

print(" Aplicando regras de recuperação e imputação temporal...")
df_full = df_full.sort_values(by=["id_cliente", "mes_referencia"])

# 1. Correção de Escala na Renda Mensal (Mês 08)
mask_erro_renda = df_full["mes_referencia"] == "2025-08"
df_full.loc[mask_erro_renda, "renda_mensal"] = (
    df_full.loc[mask_erro_renda, "renda_mensal"] / 100
)

# 2. Imputação de Idade via Mediana Temporal (Mês 11)
df_full["idade_mediana_historica"] = df_full.groupby("id_cliente")[
    "idade"
].transform("median")

mask_erro_idade = (df_full["mes_referencia"] == "2025-11") & (
    (df_full["idade"] - df_full["idade_mediana_historica"]).abs() > 2
)
df_full.loc[mask_erro_idade, "idade"] = df_full.loc[
    mask_erro_idade, "idade_mediana_historica"
]

# Marcação de Registros Imputados
df_full["registro_imputado"] = mask_erro_renda | mask_erro_idade

# %% Segregação das Camadas
print(" Segregando as bases de acordo com as regras de governança...")
df_quarantine = df_full[~df_full["cpf_valido"]].copy()
df_valid_cpf = df_full[df_full["cpf_valido"]].copy()

df_imputed = df_valid_cpf[df_valid_cpf["registro_imputado"]].copy()
df_gold = df_valid_cpf[~df_valid_cpf["registro_imputado"]].copy()

cols_finais = [
    "mes_referencia",
    "id_cliente",
    "nome",
    "cpf",
    "idade",
    "renda_mensal",
    "endereco",
]

# Exportação para Parquet
path_gold = os.path.join(DATA_PROC_DIR, "base_gold.parquet")
path_imputed = os.path.join(DATA_PROC_DIR, "base_imputed.parquet")
path_quarantine = os.path.join(DATA_PROC_DIR, "base_quarantine.parquet")

df_gold[cols_finais].to_parquet(path_gold, index=False)
df_imputed[cols_finais].to_parquet(path_imputed, index=False)
df_quarantine[cols_finais].to_parquet(path_quarantine, index=False)

print(f" [OK] Base Gold salva ({len(df_gold):,} linhas) -> {path_gold}")
print(f" [OK] Base Imputed salva ({len(df_imputed):,} linhas) -> {path_imputed}")
print(
    f" [OK] Base Quarantine salva ({len(df_quarantine):,} linhas) -> {path_quarantine}"
)

tempo_total = time.time() - start_time

# Cálculo de Percentuais
pct_gold = (len(df_gold) / total_registros_brutos) * 100
pct_imputed = (len(df_imputed) / total_registros_brutos) * 100
pct_quarantine = (len(df_quarantine) / total_registros_brutos) * 100
pct_aproveitamento_total = pct_gold + pct_imputed

# %% Exportação do Relatório Markdown e JSON
markdown_table = f"""## 📊 Resultados e Matriz Executiva de Data Quality

Os resultados gerados automaticamente pela execução do pipeline de segregação e governança foram consolidados na tabela abaixo:

| Camada (Base) | Status do Registro | Critério de Elegibilidade / Regra | Volumetria (Linhas) | Percentual (%) |
| :--- | :--- | :--- | :---: | :---: |
| **Gold** | Íntegro de Origem | Registros com CPF válido e sem nenhuma anomalia detectada. | {len(df_gold):,} | {pct_gold:.2f}% |
| **Imputed (Silver)** | Recuperado via Histórico | CPF válido, mas com correção de escala de renda (Mês 08) ou imputação de idade (Mês 11). | {len(df_imputed):,} | {pct_imputed:.2f}% |
| **Quarantine** | Invalidador/Isolado | Registros com dígitos verificadores de CPF matematicamente incorretos. | {len(df_quarantine):,} | {pct_quarantine:.2f}% |
| **TOTAL** | **Processado** | **Aproveitamento Efetivo da Base: {pct_aproveitamento_total:.2f}%** | **{total_registros_brutos:,}** | **100,00%** |

> ⏱️ **Eficiência de Processamento:** Tempo total de validação, recuperação e gravação em `.parquet`: **{tempo_total:.2f} segundos**.
"""

path_metrics_md = os.path.join(DATA_PROC_DIR, "metrics_summary.md")
with open(path_metrics_md, "w", encoding="utf-8") as f:
    f.write(markdown_table)

metrics_json = {
    "total_registros": total_registros_brutos,
    "tempo_execucao_segundos": round(tempo_total, 2),
    "taxa_aproveitamento_pct": round(pct_aproveitamento_total, 2),
    "camadas": {
        "gold": {"linhas": len(df_gold), "pct": round(pct_gold, 2)},
        "imputed": {"linhas": len(df_imputed), "pct": round(pct_imputed, 2)},
        "quarantine": {
            "linhas": len(df_quarantine),
            "pct": round(pct_quarantine, 2),
        },
    },
}

path_metrics_json = os.path.join(DATA_PROC_DIR, "metrics.json")
with open(path_metrics_json, "w", encoding="utf-8") as f:
    json.dump(metrics_json, f, indent=4, ensure_ascii=False)

print("\n" + "=" * 65)
print(" MATRIZ EXECUTIVA DE APROVEITAMENTO DE DADOS (DATA QUALITY)")
print("=" * 65)
print(f" Total de Registros Auditados: {total_registros_brutos:,} (100.0%)")
print(f" Base GOLD (Íntegros de Origem): {len(df_gold):,} ({pct_gold:.2f}%)")
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

print(f"\n [OK] Relatório Markdown salvo em: {path_metrics_md}")
print(f" [OK] Métricas JSON salvas em: {path_metrics_json}")