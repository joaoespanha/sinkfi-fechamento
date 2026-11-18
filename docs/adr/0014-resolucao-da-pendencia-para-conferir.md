# Resolução da pendência para conferir: presa ao lançamento, lida na hora

Status: aceito, 18/11/2026

A lojista pode marcar uma pendência **para conferir** como resolvida, com uma nota obrigatória que diz o que ela é. A resolução fica presa ao lançamento (`cliente_id` + id, ADR 0009) e ao valor da pendência, e não ao item da rodada. Ela é aplicada na leitura, como o limite (ADR 0006): a rodada não muda. Escolhemos assim porque a entrada sem recebível não casa em nenhuma ingestão nova e ficava na lista para sempre, e porque uma resolução presa ao item sumiria na rodada seguinte.

## Contexto

Uma entrada sem recebível (um aporte, o Pix de um cliente) aparece como para conferir. A lojista confere e descobre o que é, mas nada tira a pendência da lista. A regra é acumulada e não tem data de início (ADR 0007), então a mesma entrada aparece em todo fechamento calculado depois que ela chegou. A conferência (ADR 0012) registra que a lojista olhou o fechamento e não resolve os itens para conferir.

## Decisões

- **Só para conferir.** Os motivos `entrada_sem_recebivel` e `pode_ser_antecipacao`, os dois de lançamento. A falta de verdade (`nao_caiu`, `caiu_em_parte`, `grupo_nao_fecha`, `chargeback`, `caiu_a_mais`, `venda_cancelada`) não se resolve: resolver esconderia dinheiro que não entrou, ou que não é da lojista, e mudaria o "pode fechar". A regra é a severidade, e por isso a chave é só o lançamento.
- **Só a lojista**, como na conferência e no limite. É ela quem sabe o que é o dinheiro. O suporte vê quem resolveu, quando e a nota.
- **Nota obrigatória**, de 1 a 200 caracteres sem contar os espaços das pontas. Sem ela, "resolvida" não diz o que a entrada era. Na tela, só texto.
- **Vale para todos os fechamentos do cliente**, lida na hora. Resolver no fechamento atual também tira a pendência dos anteriores. O resumo deles muda, o aviso de fechamento sem conferência pode sumir e o botão "Marcar como conferido" volta. Isso é o esperado: a conferência compara o resumo (ADR 0012).
- **Presa ao lançamento e ao valor.** A resolução vale enquanto o lançamento for uma pendência para conferir com o mesmo valor. Se um chargeback parcial muda o valor, a pendência volta. Se o crédito passa a casar, ela fica sem efeito, porque não há o que resolver. Se vira falta de verdade, ela nunca vale.
- **Desfazer, com histórico.** Só inserção, como a conferência e o limite. Desfazer grava um registro novo, e vale o mais recente de cada lançamento. A pendência volta para as contagens.
- **Na tela, não some.** A resolvida sai da lista de pendências, das abas e da faixa dos dias, e vai para uma seção recolhida "Resolvidas", como "Casou certo". No detalhe, aparecem quem, quando e a nota, com o botão de desfazer. Resolver pede confirmação num `<dialog>`, no padrão da conferência.
- **Rota.** `POST /clientes/{cliente_id}/resolucoes` com `{rodada_id, lancamento_id, nota}`, e `DELETE /clientes/{cliente_id}/resolucoes/{lancamento_id}`. O servidor acha o item numa rodada do próprio cliente e tira de lá a severidade e o valor. Não confia no que vem no corpo. Rodada de outro cliente, ou lançamento fora da rodada, dá 404; pendência que não é para conferir dá 422.
- **Fora do escopo: o webhook `recebivel.liquidado` (ADR 0008, #30) não muda.** A resolução é de um lançamento e não torna nenhum recebível liquidado.

## Alternativas recusadas

- **Presa ao item da rodada.** O id do item muda a cada rodada, e a pendência voltaria na ingestão seguinte.
- **Gravar a resolução na rodada.** Quebra a imutabilidade (ADR 0006).
- **Só no fechamento em que foi feita.** A entrada aparece em todos os fechamentos seguintes, e a lojista resolveria de novo toda semana.
- **Presa só ao lançamento, sem o valor.** Um chargeback parcial depois da resolução passaria sem ninguém ver.
- **Resolver também a falta de verdade.** Pediria uma chave de grupo e uma política de materialidade, que o ADR 0003 recusou.
- **O suporte também resolve.** A sinkfi passaria a decidir sobre o dinheiro do cliente.
- **Nota opcional.** Um clique a menos, mas a maioria das resoluções ficaria sem explicação para o suporte.

## Consequências

- A leitura de qualquer rodada, inclusive uma antiga em Debugar, aplica as resoluções de agora. O que a lojista viu ao conferir continua na conferência (ADR 0012).
- Quando um cliente tiver mais de uma conta, a resolução precisa da conta na chave, como o lançamento (ADR 0009).

## Testes que garantem

- `test_resolver_tira_a_pendencia_do_resumo_sem_tocar_na_rodada`
- `test_resolucao_sobrevive_a_rodada_nova`
- `test_resolucao_vale_nos_outros_fechamentos`
- `test_valor_diferente_devolve_a_pendencia`
- `test_desfazer_devolve_a_pendencia_e_guarda_o_historico`
- `test_falta_de_verdade_nao_se_resolve`
- `test_nota_vazia_ou_longa_e_recusada`
- `test_rodada_de_outro_cliente_no_corpo_devolve_404`
- `test_suporte_nao_resolve_pendencia`
- `test_suporte_ve_quem_resolveu`
- `test_lojista_nao_ve_fechamento_de_outro_cliente` (ADR 0005, já cobre as rotas novas)
- `a pendência resolvida sai da lista e vai para Resolvidas` (web)
- `a resolvida não conta nas abas nem na faixa` (web)
- `só a pendência para conferir pode ser resolvida` (web)
