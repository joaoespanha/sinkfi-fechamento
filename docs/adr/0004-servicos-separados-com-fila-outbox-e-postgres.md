# Serviços separados, com fila, outbox e Postgres

Status: aceito, 17/11/2026

O fechamento roda fora da requisição. A ingestão grava os dados e um pedido de fechamento no Postgres, uma fila entrega o pedido a um worker, e o worker roda a regra pura e grava uma rodada que não muda mais. A `api` (Python, FastAPI) só lê rodadas, e o `web` (React) só mostra a mais recente. Escolhemos essa forma porque a sinkfi atende muitas PMEs com um lote de conciliação a cada 6 horas, e porque o critério de quem avalia o desafio é ficar perto de uma aplicação real.

## Contexto

A primeira decisão era um serviço sem fila: um fechamento é um cálculo de milissegundos por cliente por semana, e não há vazão a resolver. Isso continua verdadeiro. A fila entra pelas garantias de produção: a mensagem não se perde se o worker cair, a falha passageira tenta de novo, a mensagem que sempre falha vai para a dead letter, e algo dispara a ingestão de 6 em 6 horas.

## Decisão

- **Fila:** Celery com RabbitMQ. O `beat` agenda uma tarefa de ingestão por cliente. A tarefa do Celery é uma casca fina sobre a regra.
- **Outbox:** a ingestão grava o dado e o pedido de fechamento na mesma transação. Uma tarefa periódica lê os pedidos pendentes com `FOR UPDATE SKIP LOCKED` e publica na fila.
- **Rodada imutável:** identificada por cliente, data do fechamento e hash da entrada. A mesma entrada devolve a rodada que já existe; uma entrada nova cria outra e a anterior fica guardada.
- **Banco:** Postgres, com SQLAlchemy 2 síncrono e migrações no Alembic. As classes do SQLAlchemy vivem só nos repositórios.
- **Contrato:** os tipos TypeScript do `web` são gerados do OpenAPI da `api`, e a CI falha quando há diferença.

## Alternativas recusadas

- **Um serviço só em TypeScript.** Servia se o produto atendesse uma pessoa. Com muitos clientes e um lote de 6 horas, a regra pertence ao back-end.
- **A regra chamada direto pela rota.** É o que o tamanho do problema pede, mas deixa o cálculo preso à requisição e sem retry. Fica como plano de corte: a tarefa é a mesma função, chamada de forma síncrona.
- **Fila dentro do Postgres.** Tem um container a menos e publica na mesma transação do dado, sem outbox. Recusada porque todo worker passa a consultar o banco, e porque pode ser lida como ausência de fila.
- **SQS.** Não tem servidor para cuidar e traz a dead letter pronta, mas só existe na AWS: no Docker Compose seria um emulador. Em produção na AWS seria a escolha, e o outbox torna a troca barata.
- **Publicar na fila sem outbox.** Se a gravação passar e a publicação falhar, o dado entra e a rodada não roda. O lote seguinte fecharia o buraco em 6 horas, mas a lojista ficaria esse tempo vendo "não caiu" para um dinheiro que já está no banco.

## Consequências

- O outbox pode publicar o mesmo pedido duas vezes, e o Celery pode reentregar. A rodada idempotente absorve os dois casos, mesmo quando as duas cópias rodam ao mesmo tempo: a rodada e a ingestão travam o cliente no Postgres (`pg_advisory_xact_lock`), e a segunda espera a primeira e acha a rodada pelo hash. A mesma trava impede a rodada de ler a entrada no meio de uma ingestão.
- O retry cobre uma queda do Postgres de até uns 13 minutos (10 tentativas, com espera de até 300 s). Uma queda maior manda o pedido para a dead letter, e como o outbox já o deu por publicado, o fechamento só volta na ingestão seguinte. A espera máxima fica abaixo do `consumer_timeout` do RabbitMQ (30 min), porque a tentativa agendada fica no worker sem ack.
- O relay do outbox só marca o pedido como publicado depois que o RabbitMQ confirma que guardou a mensagem (`confirm_publish`).
- O processo que morre conta como tentativa, e a tarefa presa passa por um limite de tempo: as duas terminam na dead letter, em vez de voltar para a fila sem fim. O limite duro, que só existe como rede de segurança, perde a mensagem sem dead letter.
- O outbox não resolve o atraso do dado bancário (o crédito de sexta que só aparece no domingo). Ele só garante que todo dado novo vire um pedido de rodada. Quem resolve o caso é o casamento separado do corte (ADR 0001) e a rodada nova.
- O `beat` precisa ter exatamente uma cópia. `api` e `worker` não guardam estado e podem ter várias. A ingestão segue o relógio (0, 6, 12 e 18h UTC), e não a hora em que o `beat` subiu: assim um deploy não a adia.
- O primeiro limite de escala é o Postgres: a escrita tem um nó só, e muitos workers pedem um pool de conexões.
- Acesso síncrono ao banco basta enquanto a `api` só fizer consultas curtas. Se ela passar a esperar um serviço externo dentro da requisição, vale trocar para assíncrono.
- O Docker Compose tem seis serviços ligados (`postgres`, `rabbitmq`, `api`, `worker`, `beat`, `web`) e dois que rodam uma vez: `migrar` (as migrações) e `semear` (o seed e a primeira ingestão, só na demonstração).

## Testes que garantem

- `mesma_entrada_devolve_a_rodada_que_ja_existe`
- `entrada_nova_cria_rodada_e_guarda_a_anterior`
- `ingestao_grava_dado_e_pedido_na_mesma_transacao`
- `relay_nao_publica_o_mesmo_pedido_em_duas_execucoes`
- `pedido_repetido_nao_duplica_rodada`
- `dois_pedidos_ao_mesmo_tempo_devolvem_a_mesma_rodada`
- `rodada_espera_a_ingestao_em_andamento`
- `banco_fora_do_ar_tenta_de_novo` e `erro_que_nao_e_passageiro_falha_de_primeira`
- `aguenta_dez_minutos_de_banco_fora_do_ar`
- `reiniciar_o_beat_nao_adia_a_ingestao`
- `publicar_espera_o_rabbitmq_confirmar`
- `mensagem_que_derruba_o_processo_nao_volta_para_sempre`
- `trabalho_que_falha_de_vez_cai_na_fila_morta`
