# Auditoria de Qualidade de Dados (Data Quality Audit) — Abordagem Top-Down

Este projeto aplica um framework de **Saneamento, Validação e Governança de Dados** sobre uma série temporal de 12 meses de bases de dados financeiras com anomalias sintéticas.

## 📌 Abordagem e Metodologia (Top-Down)
1. **Nível 1 & 2 (Análise Macro):** Inspeção de volumetria e distribuição temporal por lotes para identificação de falhas de ingestão e escala.
2. **Nível 3 (Amostragem & Validação Micro):** Aplicação de amostragem estatística estratificada e validação sintática (algoritmo real de verificação de CPF e consistência temporal de renda/idade).
3. **Nível 4 (Segregação & Imputação Lógica):** Recuperação de registros via histórico temporal e segregação final nas camadas **Gold**, **Silver (Imputados)** e **Quarantine**.

## 🛠️ Tecnologias Utilizadas
- Python 3.10+
- Pandas, NumPy, Seaborn & Matplotlib
- PyArrow (para gravação em formato Parquet)
- Faker (geração de dados sintéticos)