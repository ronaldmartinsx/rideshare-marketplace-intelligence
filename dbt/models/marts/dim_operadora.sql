-- Dimensão de operadoras (Gold). Grão: uma linha por licença HVFHS.
-- Juno (HV0002) e Via (HV0004) estão inativas no recorte, mas ficam: uma licença histórica
-- precisa continuar resolvendo se aparecer num mês antigo.

select
    licenca      as operadora_id,
    operadora,
    ativa        as is_ativa
from {{ ref('seed_operadoras') }}
