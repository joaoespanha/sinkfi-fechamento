# sinkfi: o fechamento da segunda

A Marina abre a tela na segunda à noite e vê quanto faltou cair na conta, em quais itens, e o que ainda precisa conferir. O suporte vê o mesmo fechamento que ela.

- O desafio está em [`ENUNCIADO.md`](ENUNCIADO.md).
- As escolhas de produto e o desenho estão em [`DECISOES.md`](DECISOES.md).

## Como chegar

Precisa de Docker com Compose. Na raiz do repositório:

```sh
docker compose up -d --build --wait
```

Abra http://localhost:8080. Se a porta estiver ocupada, use `WEB_PORT=8088 docker compose up -d --build --wait`.

Na primeira subida, o `semear` cria a Marina, ingere os CSVs de `dados/` e roda o fechamento de 10/11. Rodar de novo não repete nada.

A porta escuta só em `127.0.0.1` (ADR 0013). Para abrir de outra máquina, use um túnel: `ssh -L 8080:localhost:8080 <servidor>`.

| Entrar como | E-mail | Senha |
| --- | --- | --- |
| Lojista, a Marina | `marina@sinkfi.demo` | `marina-demo` |
| Suporte | `suporte@sinkfi.demo` | `suporte-demo` |

As senhas só valem para a demonstração. A lojista cai direto no fechamento dela. O suporte acha a cliente pela busca, por e-mail, CNPJ ou nome (ADR 0010). Tente `marina`.

| | Computador | Celular (390 px) |
| --- | --- | --- |
| A lojista vê quanto faltou e quando os dados chegaram | <img src="assets/telas/lojista.png" width="480"> | <img src="assets/telas/lojista-390.png" width="180"> |
| Ela marca a rodada como conferida, o que não trava nada (ADR 0012) | <img src="assets/telas/conferencia-dialogo.png" width="480"> | <img src="assets/telas/conferencia-dialogo-390.png" width="180"> |
| A conferência fica registrada com quem conferiu e quando | <img src="assets/telas/conferido.png" width="480"> | <img src="assets/telas/conferido-390.png" width="180"> |
| O suporte vê o que a Marina vê e quando ela conferiu | <img src="assets/telas/suporte.png" width="480"> | <img src="assets/telas/suporte-390.png" width="180"> |

## Testar com outros dados

A ingestão lê `dados/`: `lojas.csv`, `recebiveis.csv` e `extrato.csv`, com as mesmas colunas de hoje.

- **Mudar linhas com a stack de pé.** Edite os CSVs e peça a ingestão na hora:

  ```sh
  docker compose exec worker celery -A sinkfi.tarefas call sinkfi.agendar_ingestoes
  ```

  Em uns 20 segundos, a tela mostra uma rodada nova, depois de recarregar. Sem esse comando, o `beat` ingere às 0, 6, 12 e 18h UTC.
- **Trocar o conjunto inteiro.** A ingestão sobrescreve a linha pelo `id`, mas não apaga: uma linha tirada do CSV continua no banco. Para começar de um conjunto novo, apague o banco com `docker compose down -v` e suba de novo.
- **Outras datas.** Os cortes andam de 7 em 7 dias a partir de 10/11 às 18:00, a data com que os CSVs do desafio batem (ADR 0007). Dados de outra semana caem nesses cortes, e a tela navega entre elas. Se o corte for em outro dia ou hora, troque a âncora, por exemplo `SINKFI_ANCORA_DOS_CORTES=2026-11-16T18:00:00-03:00 docker compose up -d --wait`. Com ela vazia, vale o dia de fechamento do cliente.

O `backend/README.md` tem mais detalhes sobre a fila, o worker e a dead letter.

## Saúde e operação

O `/api/health` não pede login e diz se a api fala com o Postgres e com o broker. O `GET /operacao` mostra a fila, a dead letter e as ingestões atrasadas. Ele é feito pelo `/api/docs`, logado como suporte. O roteiro de plantão está em [`docs/debugar.md`](docs/debugar.md), seção 6.

## Onde está cada coisa

| O quê | Onde |
| --- | --- |
| Escolhas de produto e desenho | [`DECISOES.md`](DECISOES.md) |
| Decisões com contexto e alternativas | [`docs/adr/`](docs/adr/) (0001 a 0013) |
| Roteiro de "o número não bate" | [`docs/debugar.md`](docs/debugar.md) |
| Vocabulário do domínio | [`GLOSSARY.md`](GLOSSARY.md) |
| Leitura dos dados da semana | [`analise/ANALISE-DADOS.md`](analise/ANALISE-DADOS.md) |
| A regra do fechamento, pura | `backend/src/fechamento/` |
| Api, fila e banco | `backend/src/sinkfi/` ([`backend/README.md`](backend/README.md)) |
| A tela | `web/` ([`web/README.md`](web/README.md)) |

## Testes

```sh
cd backend && uv run pytest   # os de integração sobem Postgres e RabbitMQ com Docker
cd web && npm ci && npm test
```

A CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) roda os dois e o build. Ela também confere se os tipos da tela batem com o OpenAPI da api.
