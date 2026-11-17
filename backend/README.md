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

A `api` assina o cookie de sessão com `JWT_SECRET`. O `compose.yaml` traz um valor de demonstração; fora dela, passe o seu (`JWT_SECRET=... docker compose up`).

## Fila, worker e beat

O fechamento roda fora da requisição (ADR 0004): o `beat` agenda a ingestão de cada cliente a cada 6 horas, e o `worker` ingere e roda o fechamento vigente. O `POST /clientes/{id}/reprocessar` só enfileira e responde 202.

```sh
docker compose up --build -d worker beat
```

- **Disparar o agendamento na hora**, sem esperar 6 horas: `docker compose exec worker celery -A sinkfi.tarefas call sinkfi.agendar_ingestoes`.
- **Fonte da ingestão:** uma pasta por cliente em `PASTA_DADOS`. Na demonstração, `dados/` é montada como a pasta da `cli_marina`.
- **Corte da demonstração:** os CSVs batem com o corte de 10/11, que não é um dia de fechamento da Marina. Por isso o worker recebe `SINKFI_CORTE_FIXO`; com ela vazia (`SINKFI_CORTE_FIXO= docker compose up ...`), vale o fechamento vigente, e a tela passa a mostrar a rodada de hoje.
- **Retry e dead letter:** banco fora do ar tenta de novo até 5 vezes, com espera crescente. Qualquer outra falha vai para a fila `fechamento.morta`, visível no painel do RabbitMQ em `localhost:15672` (`guest`/`guest`).
- **Api fora do compose** (o uvicorn local): passe `BROKER_URL=amqp://guest:guest@localhost:5672//`.
