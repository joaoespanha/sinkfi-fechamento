# O que a rodada grava: cópia do que usou, versão da regra e corte no hash, limite fora

Status: aceito, 17/11/2026

Cada rodada guarda uma cópia dos recebíveis e créditos que cada item usou. A rodada é identificada por cliente, data do fechamento e um hash que cobre a entrada, o corte e a versão da regra. O limite da trava fica fora da rodada: o resumo é calculado na leitura. Escolhemos assim para que um número antigo possa ser explicado exatamente como a lojista o viu, e para que uma correção na regra nunca devolva uma rodada errada.

## Contexto

O ADR 0004 tornou a rodada imutável, mas não disse o que ela guarda. A entrada vive em tabelas que a ingestão atualiza: quando o `rec_7001` é reenviado como cancelado, a tabela `recebiveis` muda. Se a rodada guardasse só ids, a rodada antiga passaria a mostrar o cancelamento.

O fechamento da segunda às 18:00 é da Marina, não do sistema. Outros clientes podem fechar em outros dias.

## Decisões

- **Cópia em JSONB por item.** `rodadas` e `itens_rodada` guardam os valores, a severidade, o motivo e a chave em colunas, e os recebíveis e créditos do item em JSONB, como estavam na hora do cálculo. Um índice GIN atende "em quais rodadas o `rec_7001` apareceu".
- **Versão da regra no hash.** Sem ela, a mesma entrada depois de um bug corrigido devolveria a rodada antiga, calculada com o bug.
- **Corte como entrada.** A regra recebe o corte com fuso e não sabe o que é "segunda". Dia, hora e fuso do fechamento são configuração do cliente. `fechamento_vigente(config, agora)` escolhe o corte, e um fechamento continua recebendo rodadas até passar o corte seguinte, para pegar o crédito atrasado e o chargeback depois das 18:00.
- **Limite fora do hash.** O limite é uma preferência da lojista, não um dado do fechamento. Mudá-lo não cria rodada nem passa pela fila. A conferência (ADR 0012) grava o limite e o resumo daquele momento, e cada mudança de limite fica registrada.

## Alternativas recusadas

- **Rodada guarda só ids das tabelas atuais.** Quebra a imutabilidade.
- **Recebíveis e lançamentos versionados, rodada aponta para a versão.** É o modelo mais limpo, sem duplicação, mas a ingestão passa a comparar e versionar cada linha. Custa meio dia no mínimo. É o próximo passo se a duplicação pesar.
- **Entrada inteira do lote guardada com o hash.** Permite reprocessar, mas consultar um item exige abrir o lote todo.
- **Limite dentro do hash.** Cada mudança de limite geraria uma rodada nova pela fila, e a lojista esperaria um lote para ver o resumo mudar.
- **Corte fixo em segunda às 18:00 no código.** Serve só para a Marina.

## Consequências

- Os dados ficam duplicados a cada rodada nova.
- O resumo de uma rodada antiga é lido com o limite atual. O que a lojista viu ao conferir está na conferência (ADR 0012).
- Mudar a versão da regra faz todo cliente ganhar uma rodada nova no lote seguinte, mesmo sem dado novo.
- Fechamento mensal ou quinzenal exigiria trocar o dia do fechamento por uma regra de periodicidade.

## Testes que garantem

- `rodada_antiga_nao_muda_quando_recebivel_e_cancelado`
- `versao_nova_da_regra_cria_rodada_nova_com_mesma_entrada`
- `item_guarda_copia_dos_recebiveis_e_creditos`
- `busca_rodadas_por_recebivel`
- `mudar_limite_nao_cria_rodada_nova`
- `resumo_usa_o_limite_atual_na_leitura`
- `fechamento_vigente_de_cliente_de_segunda_na_terca_e_o_da_segunda_anterior`
- `cliente_de_sexta_tem_corte_na_sexta`
- `corte_diferente_gera_hash_diferente`
