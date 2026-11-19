"""Constantes e decisões de modelagem da previsão de demanda (Fase 5, passo 5).

Tudo que é escolha — quais colunas o modelo vê, com que tipo, e com que parâmetros treinar — fica
aqui, num lugar só, para a decisão ser revisável sem ler o código de treino.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Origem dos dados
# ---------------------------------------------------------------------------

BANCO = {"dev": "dev_gold", "prod": "gold"}  # mesma convenção da macro generate_schema_name do dbt
WORKGROUP = "rideshare"                      # limite de 3 GiB por consulta (spec 11.4)

TABELA_FEATURES = "ml_features_demanda"
TABELA_BASELINE = "ml_baseline_demanda"

# Binário do modelo treinado. Vai para o S3, nunca para o Git: Git é para código, modelo é dado.
BUCKET_MODELOS = "rmartins-rideshare-lake"
PREFIXO_MODELOS = "ml/modelos"

# ---------------------------------------------------------------------------
# Colunas: o que trazer do Athena
# ---------------------------------------------------------------------------
# Trazer a tabela toda sem pensar é o caminho mais curto para o contêiner morrer sem explicação
# (Aula 4). Ficam de fora, de propósito:
#   hora_lag_1             - é auditoria (prova o antivazamento no SQL), o modelo não usa
#   alvo_zero_por_ausencia - auditoria da série limpa
#   hora_dobrada           - 1 hora em 26.304; não compensa carregar 6,3 M de booleanos por isso

CHAVES = ["hora_alvo", "zona_id"]                # identificam a linha e religam a previsão à tabela
CONTROLE = ["mes_corte", "mes_alvo", "tem_alvo"]  # recortam treino, teste e produção
COLUNA_ALVO = "qtd_corridas"

# A coluna `corte` (timestamp) NÃO é lida de propósito. Medido em 15/11/2026: ela custava 48,2 MB de
# memória, a segunda coluna mais pesada da tabela, e não acrescenta nada — existe um corte por mês, e
# o mes_corte já o identifica. O timestamp é recuperável a qualquer momento (é a última hora do mês).
# A ml_forecast_demanda da spec 6.4 tem grão hora-alvo × zona × execução, e também não pede o corte.

# Timestamps que precisam de cast na consulta. O Iceberg cria timestamp(6) (microssegundo), e o
# UNLOAD do Athena só exporta Parquet até precisão de MILISSEGUNDO — sem o cast ele falha com
# "Incorrect timestamp precision for timestamp(6)". A conversão é sem perda: hora_alvo é hora cheia.
COLUNAS_TIMESTAMP = ["hora_alvo"]

# As features propriamente ditas, na ordem em que entram no modelo.
COLUNAS_FEATURE = [
    # A FOTO: a demanda passada, medida antes do corte (decisão D1)
    "lag_1_semana",
    "lag_2_semanas",
    "lag_3_semanas",
    "lag_4_semanas",
    # Quão velha está a foto. O modelo aprende sozinho a confiar menos em horizonte longo.
    "horizonte_horas",
    # A zona, como CATEGORIA e não como número (ver CATEGORICAS_LIGHTGBM abaixo)
    "zona_id",
    # Calendário: conhecido com anos de antecedência, é o que permite ANTECIPAR em vez de só reagir
    "hora_do_dia",
    "dia_da_semana",
    "hora_da_semana",
    "is_fim_de_semana",
    "is_feriado_observado",
    "nome_feriado_observado",
    "tipo_dia_observado",
    "mes_do_ano",
    # Clima OBSERVADO: o vazamento ACEITO e documentado (spec 9.1). Em produção só existiria
    # previsão do tempo, com erro, o que torna o resultado do backtest otimista.
    "clima_obs_temperatura_c",
    "clima_obs_precipitacao_mm",
    "clima_obs_chuva_mm",
    "clima_obs_neve_cm",
    "clima_obs_vento_kmh",
]


def _sem_repetir(*listas: list[str]) -> list[str]:
    """Junta as listas preservando a ordem e descartando repetição.

    A zona_id aparece de propósito em CHAVES e em COLUNAS_FEATURE: ela identifica a linha E é
    feature do modelo global (spec 9.1). Sem esta função, a lista de leitura pediria
    "select zona_id, ..., zona_id" e o pandas receberia coluna duplicada.
    """
    vistas: dict[str, None] = {}
    for lista in listas:
        for coluna in lista:
            vistas.setdefault(coluna, None)
    return list(vistas)


COLUNAS_LEITURA = _sem_repetir(CHAVES, CONTROLE, [COLUNA_ALVO], COLUNAS_FEATURE)

# A hora_da_semana (0 a 167) é derivável de dia_da_semana e hora_do_dia, então não acrescenta
# INFORMAÇÃO. Entra ainda assim porque acrescenta EFICIÊNCIA à árvore: isolar "sexta à noite" custa
# um corte nela e dois nas outras duas. Árvore não se incomoda com feature redundante.
#
# Ficam FORA das features, de propósito: mes_corte e mes_alvo. Elas deixariam o modelo decorar meses
# específicos, que nunca se repetem no futuro — é overfitting garantido e sem utilidade em produção.
# Entram apenas como recorte (CONTROLE).

# ---------------------------------------------------------------------------
# Tipos: onde a memória é ganha ou perdida
# ---------------------------------------------------------------------------
# Texto repetitivo vira CATEGORIA. Medido na Aula 4: mes_corte e mes_alvo, com 33 valores distintos
# cada em 6,3 M de linhas, custam 673 MB como texto e 12 MB como categoria — 56x. O VertiPaq do
# Power BI faz isso sozinho; o pandas só faz se a gente pedir.
# SÓ COLUNAS DE TEXTO. Medido em 15/11/2026: pedir o zona_id como categoria na leitura quebra o modo
# UNLOAD com "NotImplementedError: dictionary<values=int32, indices=int32>" — o leitor de Parquet não
# converte dicionário de inteiros. E não precisa: o zona_id fica int32 (24 MB, barato) e é declarado
# como categórico direto para o LightGBM, em CATEGORICAS_LIGHTGBM. O parâmetro `categories` do
# awswrangler existe para texto, que é onde está o problema de memória de verdade.
COLUNAS_CATEGORIA = [
    "mes_corte",
    "mes_alvo",
    "tipo_dia_observado",       # 3 valores: util, fim_de_semana, feriado
    "nome_feriado_observado",   # 11 feriados federais
]

# float32 em vez de float64 nos números grandes: metade da memória, e exato para inteiro até 16,7
# milhões (a demanda máxima medida é ~1.700). Os lags precisam ser float e não int porque podem ser
# NULOS (1.048 casos, o lag que cai na 2h inexistente de março) — e o LightGBM trata nulo nativamente.
DTYPES = {
    "lag_1_semana": "float32",
    "lag_2_semanas": "float32",
    "lag_3_semanas": "float32",
    "lag_4_semanas": "float32",
    "clima_obs_temperatura_c": "float32",
    "clima_obs_precipitacao_mm": "float32",
    "clima_obs_chuva_mm": "float32",
    "clima_obs_neve_cm": "float32",
    "clima_obs_vento_kmh": "float32",
    "horizonte_horas": "int16",   # 1 a 744, cabe
    "hora_do_dia": "int8",        # 0 a 23
    "dia_da_semana": "int8",      # 1 a 7
    "hora_da_semana": "int16",    # 0 a 167
    "mes_do_ano": "int8",         # 1 a 12
    "qtd_corridas": "float32",    # pode ser nulo no "dia de valer"
    # zona_id chega como Int32 ANULÁVEL do pandas (30 MB). Ele nunca é nulo — tem teste not_null
    # no _gold.yml — então vira int32 simples: 6 MB menos e nenhum tipo anulável chegando ao
    # LightGBM, que lida mal com os dtypes de extensão do pandas.
    "zona_id": "int32",
    # Com dtype_backend="pyarrow" na leitura (ver dados.py), TODAS as colunas voltam com tipo Arrow.
    # Estas duas precisam virar tipo nativo porque são USADAS em operação, não só lidas:
    # tem_alvo entra em máscara booleana (dados.recortar) e hora_alvo entra na junção com o
    # baseline. Tipo de extensão nessas duas é pedir surpresa.
    "tem_alvo": "bool",
    "hora_alvo": "datetime64[ns]",
    # E estas duas são FEATURES booleanas: vão direto para o LightGBM, que lida mal com tipo de
    # extensão do pandas. Faltaram na primeira versão e a conferência as pegou (19/11/2026).
    "is_fim_de_semana": "bool",
    "is_feriado_observado": "bool",
}

# ---------------------------------------------------------------------------
# LightGBM
# ---------------------------------------------------------------------------
# Colunas que o LightGBM deve tratar como CATEGÓRICAS, e não como números ordenados.
# A zona_id é o caso crítico: a zona 132 não é "o dobro" da 61 nem "maior" que ela. Tratada como
# número, a árvore faria cortes do tipo "zona_id <= 96", que não significam nada. Tratada como
# categoria, ela agrupa zonas por comportamento — que é o ponto do modelo GLOBAL da spec 9.1.
CATEGORICAS_LIGHTGBM = ["zona_id", "tipo_dia_observado", "nome_feriado_observado"]

PARAMS_LIGHTGBM = {
    # objective L1 (erro absoluto) e NÃO L2 (erro quadrático), por um motivo exato:
    # WAPE = soma|real - previsto| / soma(real). O denominador é fixo dado o conjunto avaliado, então
    # minimizar a soma dos erros absolutos É minimizar o WAPE. L2 minimizaria o erro ao quadrado, o
    # que persegue os picos e piora a métrica que a fase escolheu. A função de perda tem de combinar
    # com a métrica de avaliação; quando não combina, o modelo otimiza a coisa errada com competência.
    "objective": "regression_l1",
    "metric": "mae",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_data_in_leaf": 100,     # com 6,3 M de linhas, folha com menos que isso é ruído
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 1,
    "num_threads": 4,            # contêiner local; não adianta pedir mais núcleo do que há
    "verbose": -1,
    # REPRODUTIBILIDADE. O "pronto quando" da fase (spec, Seção 12) exige que o backtest rode de
    # forma reprodutível, então a semente é fixa e o modo determinístico está ligado. Sem isso, dois
    # treinos no mesmo dado dariam WAPEs ligeiramente diferentes e a comparação com o baseline
    # perderia sentido.
    "seed": 42,
    "deterministic": True,
    "force_row_wise": True,      # evita o aviso de overhead e fixa a estratégia de construção
}

# Número fixo de árvores, sem early stopping nesta versão.
# Early stopping exigiria um conjunto de validação, e escolher esse conjunto por amostragem
# aleatória seria vazamento (Aula 2, nº 3). Fazer certo exige mais um recorte temporal dentro do
# treino, o que fica como melhoria registrada em vez de complexidade escondida.
N_ARVORES = 500
