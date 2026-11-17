# Webhook `recebivel.liquidado`: o Postgres decide quando, a fila só distribui

Status: aceito, 17/11/2026

O cliente enterprise recebe no ERP um evento `recebivel.liquidado` quando um recebível casou certo. O evento nasce na mesma transação da rodada e é único por recebível. A entrega, as tentativas e a hora da próxima tentativa ficam no Postgres. O beat enfileira o que venceu, e um worker assina e faz o POST. A base é o desenho de system design do webhook, adaptado ao ADR 0004: RabbitMQ no lugar do SQS e beat no lugar do processo de 1 minuto.

## Contexto

O fechamento diz à Marina o que caiu, mas o ERP dela continua sem saber: alguém ainda digita a baixa de cada venda. O cliente maior quer que a baixa entre sozinha. O que ele precisa é de um fato estável por recebível, e não do resumo da semana, que muda a cada rodada.

## Decisões

- **Liquidado é o grupo que casou certo até o corte:** sem pendência, sem "não caiu" e sem "próximo fechamento". Um grupo pela metade não gera evento, porque a regra não escolhe qual venda foi paga (ADR 0002). Um crédito que caiu depois do corte gera o evento na rodada da semana seguinte.
- **O evento nasce na transação da rodada**, como o pedido nasce na transação do dado (ADR 0004). É único por (recebível, tipo): rodada nova, reprocessamento e semana anterior não repetem o evento. O corpo congela quando o evento nasce.
- **A entrega é única por (evento, endpoint)** e só nasce para endpoint ativo. Ela leva o `cliente_id`, e o worker confere que a entrega e o endpoint são do mesmo cliente antes de enviar.
- **O retry mora no Postgres:** a entrega guarda a hora da próxima tentativa, nos intervalos 1 min, 5 min, 30 min, 2 h, 5 h e 10 h, e depois 24 h até dar uns 3 dias. Depois disso, fica `falhou`. Ao enfileirar, o beat empurra essa hora por um prazo, e a mensagem perdida volta sozinha quando ele vence.
- **Uma fila `webhook` com a própria dead letter.** Um ERP lento ocupa os workers dessa fila, e não os do fechamento.
- **Nenhuma transação fica aberta durante o POST.** A entrega é pelo menos uma vez, e o ERP deduplica pelo id do evento.
- **A assinatura segue o Standard Webhooks:** HMAC-SHA256 de `id.timestamp.corpo`, nos cabeçalhos `webhook-id`, `webhook-timestamp` e `webhook-signature`. O cliente pode usar uma biblioteca pronta para conferir.
- **O segredo fica cifrado no banco**, com a chave numa variável de ambiente.
- **Só HTTPS e nenhum IP interno**, conferidos a cada envio, sem seguir redirecionamento. Uma variável libera a rede interna, e só a demonstração a liga.
- **Um endpoint por cliente** nesta fatia. A tabela de entregas já aceita vários.
- **O `webhook.teste` é um evento sem recebível**, criado pelo suporte para um endpoint só. Ele cobre o caso de quem acabou de cadastrar uma URL, já que os eventos antigos não nascem de novo.

## Alternativas recusadas

- **Um evento por rodada (`fechamento.calculado`).** É a unidade natural da casa, mas o ERP teria que comparar resumos para descobrir o que mudou. O fato estável é o recebível.
- **O `retry` com `countdown` do Celery.** Dá menos código, mas a espera fica dentro do broker: o suporte não enxerga a próxima tentativa, e perder o broker perde a agenda.
- **Segurar a linha da entrega durante o POST.** Evita a entrega em dobro, mas prende uma conexão do banco por até 15 s para cada ERP lento.
- **Repetir os eventos antigos quando a URL muda.** Quem troca de URL não espera receber de novo o que já foi entregue. Para isso existe o "Reenviar", entrega por entrega.

## Consequências

- Um chargeback depois do evento não desfaz o evento: o ERP já deu baixa. O `recebivel.estornado` fica para a próxima fatia, e até lá o suporte resolve à mão.
- O evento chega até um ciclo de ingestão depois do crédito, de 6 em 6 horas. Não é tempo real.
- A conferência de IP acontece antes da conexão, então um DNS que muda entre a conferência e o POST passa por ela. Quem fecha esse buraco é o proxy de saída isolado, que fica fora da fatia.
- Ficam fora da fatia, cada um com o seu gatilho: SNS para um segundo consumidor interno, fan-out por tipo de evento, fila de retry separada, pausa automática do endpoint, proxy de saída isolado, IP fixo de saída e alertas para o suporte e os engenheiros.

## Testes que garantem

- `recebivel_casado_certo_gera_evento_liquidado`
- `credito_depois_do_corte_ainda_nao_gera_evento`
- `rodada_nova_nao_repete_o_evento_do_mesmo_recebivel`
- `worker_recusa_entrega_de_endpoint_de_outro_cliente`
- `entrega_que_falha_agenda_a_proxima_no_intervalo_seguinte`
- `relay_nao_enfileira_a_mesma_entrega_em_dois_ticks`
- `url_http_ou_ip_interno_e_recusada_sem_a_liberacao`
