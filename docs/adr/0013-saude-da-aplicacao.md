# Saúde da aplicação: `/health` aberto, health checks no compose e a ingestão como pulso do beat

Status: aceito, 18/11/2026

A aplicação diz se está de pé em dois lugares:

- **`GET /health`**, sem login. Confere se a api fala com o Postgres e com o broker. É ele que os health checks do compose chamam.
- **`GET /operacao`**, só para o suporte. Mostra se o trabalho anda: a fila, a dead letter e, agora, a ingestão.

Quem consulta é o suporte ou a engenharia, pelo `/api/docs` e pelo roteiro em `docs/debugar.md`. Escolhemos assim porque o caso que escapava era o beat parado: sem ingestão não entra pedido no outbox, e a fila parecia saudável.

## Decisões

- **`/health` é a única rota em inglês.** Load balancers e sondas de orquestrador procuram esse nome por convenção.
- **O `/health` responde 200 ou 503** com `ok` ou `falhou` para `postgres` e `broker`, e mais nada. A rota é aberta, então não expõe versão, host nem mensagem de erro.
- **Uma rota só, sem divisão em `/health/live` e `/health/ready`.** O compose não age sobre "unhealthy": só reinicia o processo que sai. A divisão só faria diferença num orquestrador.
- **Health checks:**
  - **api:** o `/health` direto.
  - **web:** o `/health` através do nginx, o que pega também o repasse quebrado.
  - **worker:** `celery inspect ping` só no próprio nó. Leva cerca de 1 s, e o intervalo é de 30 s.
- **O beat não tem health check.** Não há o que perguntar a ele. A morte dele aparece pela ingestão no `/operacao`:
  - `ultima_ingestao_em`, a mais recente de todos os clientes;
  - `clientes_com_ingestao_atrasada`, pela mesma regra de 12 h da linha de atualização (ADR 0011), com o relógio da api. Assim o suporte e a lojista concordam sobre quem está atrasado.
- **`restart: unless-stopped`** nos serviços longos. Não entra em `migrar` nem em `semear`, que rodam uma vez.
- **O nginx resolve o nome da api pelo DNS do Docker a cada 10 s.** Antes ele guardava o IP da subida e respondia 502 depois que a api era recriada.
- **As portas publicadas ficam só no `127.0.0.1`.** O web e o Postgres escutavam em todas as interfaces. De fora, o acesso é por túnel ou por um proxy com TLS.

## Alternativas recusadas

- **Uma tela de operação para o suporte.** O `/api/docs` com o login do suporte já serve à consulta. A tela fica em "com mais tempo", junto com Prometheus e alertas.
- **Um health check no beat** que olhasse o arquivo de agenda. Ele diria que o processo existe, não que a ingestão roda. A ingestão atrasada responde à pergunta que importa.
- **Calcular o atraso pelo relógio do banco**, como a idade do pedido pendente. A regra das 12 h ficaria duplicada em SQL, e o suporte e a lojista poderiam discordar.

## Consequências

- **"Unhealthy" só avisa.** Um container travado e de pé não é reiniciado pelo compose. Num orquestrador, o health check da api passaria a reiniciar o container, e aí a divisão entre live e ready vira necessária: um broker fora não deve reiniciar a api.
- **Com o broker fora, a api e o web ficam unhealthy**, embora a leitura do fechamento continue funcionando. Aceitamos, porque o reprocessar e o `/operacao` dependem dele.

## Testes que garantem

- `test_health_responde_ok_com_banco_e_broker_no_ar` (sem login), `test_health_responde_503_e_nomeia_o_broker_quando_ele_cai`, `test_health_responde_503_quando_o_banco_cai`
- `test_operacao_lista_cliente_com_ingestao_ha_mais_de_doze_horas`, `test_operacao_nao_lista_cliente_com_ingestao_ha_doze_horas`, `test_operacao_nao_lista_cliente_sem_ingestao`, `test_operacao_devolve_a_ingestao_mais_recente_de_todos`
- Na stack, à mão:
  - `docker compose ps` com api, web e worker healthy;
  - a api recriada sem 502;
  - o RabbitMQ parado deixando a api e o web unhealthy;
  - o worker morto voltando sozinho.
