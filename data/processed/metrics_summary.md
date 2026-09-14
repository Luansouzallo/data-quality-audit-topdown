## 📊 Resultados e Matriz Executiva de Data Quality

Os resultados gerados automaticamente pela execução do pipeline de segregação e governança foram consolidados na tabela abaixo:

| Camada (Base) | Status do Registro | Critério de Elegibilidade / Regra | Volumetria (Linhas) | Percentual (%) |
| :--- | :--- | :--- | :---: | :---: |
| **Gold** | Íntegro de Origem | Registros com CPF válido e sem nenhuma anomalia detectada. | 492,615 | 87.19% |
| **Imputed (Silver)** | Recuperado via Histórico | CPF válido, mas com correção de escala de renda (Mês 08) ou imputação de idade (Mês 11). | 55,741 | 9.87% |
| **Quarantine** | Invalidador/Isolado | Registros com dígitos verificadores de CPF matematicamente incorretos. | 16,644 | 2.95% |
| **TOTAL** | **Processado** | **Aproveitamento Efetivo da Base: 97.05%** | **565,000** | **100,00%** |

> ⏱️ **Eficiência de Processamento:** Tempo total de validação, recuperação e gravação em `.parquet`: **5.94 segundos**.
