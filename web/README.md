# web

A tela do fechamento: React, Vite e TypeScript.

## Subir tudo

Na raiz do repositório:

```sh
docker compose up --build semear web
```

Abra http://localhost:8080. Se a porta estiver ocupada, `WEB_PORT=8088 docker compose up ...`.

O nginx serve a tela e repassa `/api` para a `api`. A documentação da api fica em http://localhost:8080/api/docs.

## Contrato com a api

Os tipos de `src/api.d.ts` são gerados do OpenAPI da api (ADR 0004). Mudou um esquema em `backend/src/sinkfi/api/esquemas.py`, rode:

```sh
npm run contrato
```

A CI regera o arquivo e falha se ele estiver diferente do que está no repositório.

## Desenvolvimento

Com o Postgres do compose de pé e a api rodando em `localhost:8000`:

```sh
npm install
npm run dev
```

O Vite repassa `/api` para `API_URL` (padrão `http://localhost:8000`).
