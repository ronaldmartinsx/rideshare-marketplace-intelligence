# ADR 0022: Código de ML em `airflow/include/ml/`, não em `ml/` na raiz

- **Status:** Decidido e aplicado na Fase 5 (passo 5)
- **Data:** 15/11/2026
- **Fase:** 5
- **Relacionado:** spec 11.1 (estrutura do repositório), spec 9.1 (execução numa task do Airflow), Fase 3 decisões F6 e F7

## Contexto

A spec 11.1 desenha o repositório com uma pasta **`ml/` na raiz**, ao lado de `airflow/` e `dbt/`. Mas a spec 9.1 diz que a execução é "Python numa **task do Airflow**", e as DAGs precisam importar esse código.

Todo o Python compartilhado deste projeto vive em **`airflow/include/`** e é importado como `include.*` — é assim que as cinco DAGs existentes fazem hoje:

```python
from include.dbt_construcao import planejar_construcao
from include.ingestao.ambientes import clientes_aws
```

Código na raiz não é importável de dentro do contêiner sem montagem no `docker-compose.override.yml` mais um ajuste de `PYTHONPATH`.

## Decisão

O código de ML fica em **`airflow/include/ml/`**, importado como `include.ml.*`, igual aos três módulos que já existem.

A spec 11.1 foi atualizada.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **`ml/` na raiz, montada para dentro do `include`** | Preserva o desenho da spec e segue o precedente da pasta `dbt/` (decisão F6). Mas quem lê a DAG vê `include.ml` e não encontra `include/ml/` no repositório: uma indireção a explicar para sempre, em troca de uma linha de desenho |
| **`ml/` na raiz com venv próprio, rodada como subprocesso** | Seguiria também a decisão F7 (venv separado para bibliotecas não brigarem). Mas o passo 0 mediu o risco de conflito e ele é baixo: o `awswrangler` aceita `pyarrow<27` e o projeto fixa 26.0.0, e o `lightgbm` quase não tem dependências. O dbt precisou de venv próprio porque tem árvore de dependências profunda e opinativa; aqui não é o caso |

## Consequências

- **Zero infraestrutura nova:** nenhuma montagem, nenhum `PYTHONPATH`, nenhum venv extra no Dockerfile.
- **Divergência de um desenho que já era esboço.** A spec 11.1 também não lista `scripts/`, `data/` nem `_brief/`, que existem desde a Fase 1. É um diagrama de intenção, não um contrato.
- **Vale o mesmo para a Fase 6:** o `llm/` previsto na raiz deve seguir esta decisão e nascer em `airflow/include/llm/`, pelo mesmo motivo — a DAG `llm_monthly_summary` vai importá-lo.
- **Ambiente local de desenvolvimento:** `airflow/.venv`, espelhando o `dbt/.venv` que já existe, coberto pelo `.gitignore`. Serve para rodar o código fora do contêiner. **No macOS exige `brew install libomp`**, porque o LightGBM depende de OpenMP em tempo de execução — a wheel instala sem ele, mas não carrega.
