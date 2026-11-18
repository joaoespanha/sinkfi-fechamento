# backend

Regra pura do fechamento (`src/fechamento`). Para rodar os testes:

```sh
uv run pytest
```

## Banco com os dados da Marina

Na raiz do repositório:

```sh
docker compose up --build semear
```

Sobe o Postgres, roda as migrações (`migrar`) e grava a Marina, os CSVs de `dados/` e o fechamento de 10/11 (`semear`). Os dois serviços rodam e terminam. O `semear` só existe na demonstração e pode rodar de novo sem repetir nada.

## Login da demonstração

O `semear` cria dois usuários (ADR 0005). As senhas são só de demonstração:

| Email | Senha | Papel |
| --- | --- | --- |
| `marina@sinkfi.demo` | `marina-demo` | lojista da `cli_marina` |
| `suporte@sinkfi.demo` | `suporte-demo` | suporte, vê qualquer cliente |

A `api` assina o cookie de sessão com `JWT_SECRET`, de pelo menos 32 bytes. O `compose.yaml` traz um valor de demonstração, público, e liga `SINKFI_DEMONSTRACAO=1`: sem essa variável, a api se recusa a subir com ele. Fora da demonstração, passe o seu (`JWT_SECRET=... docker compose up`) e tire o `SINKFI_DEMONSTRACAO` do compose.

## Fila, worker e beat

O fechamento roda fora da requisição (ADR 0004): o `beat` agenda a ingestão de cada cliente a cada 6 horas, e o `worker` ingere e roda o fechamento vigente. O `POST /clientes/{id}/reprocessar` só enfileira e responde 202.

```sh
docker compose up --build -d worker beat
```

- **Disparar o agendamento na hora**, sem esperar 6 horas: `docker compose exec worker celery -A sinkfi.tarefas call sinkfi.agendar_ingestoes`.
- **Fonte da ingestão:** uma pasta por cliente em `PASTA_DADOS`. Na demonstração, `dados/` é montada como a pasta da `cli_marina`.
- **Cortes da demonstração:** os CSVs batem com o corte de terça, 10/11, e a Marina fecha na segunda. Por isso a api e o worker recebem `SINKFI_ANCORA_DOS_CORTES`, que faz os cortes andarem de 7 em 7 dias a partir de 10/11 às 18:00 (ADR 0007); com ela vazia (`SINKFI_ANCORA_DOS_CORTES= docker compose up ...`), valem o dia e a hora de fechamento do cliente.
- **Retry e dead letter:** banco fora do ar tenta de novo até 10 vezes, com espera crescente de até 300 s, o que cobre uns 13 minutos de queda (ADR 0004). Qualquer outra falha vai para a fila `fechamento.morta`, visível no painel do RabbitMQ em `localhost:15672` (`guest`/`guest`).
- **Outbox:** a ingestão grava o pedido de fechamento na mesma transação do dado (tabela `pedidos_fechamento`), e o beat dispara a cada 10 segundos o relay, que publica os pendentes. O relay tem a fila própria `outbox`, sem dead letter: o tick perdido é coberto pelo próximo.
- **Api fora do compose** (o uvicorn local): passe `BROKER_URL=amqp://guest:guest@localhost:5672//` e um `JWT_SECRET` de pelo menos 32 bytes.
