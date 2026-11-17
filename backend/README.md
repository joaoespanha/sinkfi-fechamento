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
