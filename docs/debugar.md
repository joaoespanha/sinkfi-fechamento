# Debugar: "o número não bate"

O caminho da frase da lojista até o recebível, o lançamento e a decisão da regra, para quem está de plantão sem quem escreveu o código. Os termos (rodada, corte, chave forte e fraca, grupo, versão da regra) estão no `GLOSSARY.md`.

Os exemplos usam a demonstração: `docker compose up`, a tela em `http://localhost:8080` (ou o `WEB_PORT`) e a cliente `cli_marina`.

## 1. Qual rodada ela viu

Entre como suporte (`suporte@sinkfi.demo`) e abra o fechamento da cliente. O aviso do "Terminei" diz quem terminou, quando e sobre qual rodada.

- **Mesma rodada da tela:** ela viu o que você está vendo. Siga para o passo 2.
- **"O fechamento mudou desde que você terminou":** a tela mostra o resumo de antes e o de agora. A primeira pergunta é se a diferença vem dessa mudança, como um crédito que chegou depois do "Terminei". Para ver os itens da rodada antiga, use o passo 3.

## 2. Qual item

Abra a pendência que ela cita. A página do item mostra o motivo, ou a chave pela qual casou, a linha do tempo da venda até o corte, o próximo passo sugerido, e os recebíveis e créditos com NSU, valores e datas. Anote o NSU.

## 3. Em quais rodadas a venda aparece e o que a regra viu em cada uma

Com o login de suporte no mesmo navegador, abra `http://localhost:8080/api/docs`:

- `GET /clientes/{cliente_id}/rodadas?nsu=STN-1002` lista as rodadas em que a venda aparece, da mais nova para a mais antiga, com a versão da regra e o corte de cada uma. Sem `nsu`, lista todas as rodadas do cliente.
- `GET /clientes/{cliente_id}/rodadas/{rodada_id}` devolve a rodada pedida no mesmo formato do fechamento, inclusive quando ela já não é a mais recente.

Cada item traz a **cópia** do recebível e do lançamento que a regra usou naquela rodada (ADR 0006). Se o dado mudou no banco depois, a cópia continua mostrando o que a regra recebeu.

## 4. A regra de hoje decide igual

```sh
docker compose exec api python -m sinkfi.reproduzir cli_marina <rodada_id>
```

O script só lê. Ele responde três perguntas:

- **Versão da regra.** Se a rodada é de uma versão anterior, uma correção na regra pode explicar a diferença. Uma correção gera rodada nova, e nunca muda a antiga.
- **Entrada.** Recalcula o hash com o dado de hoje e o corte e a versão da rodada. Se não bate, lista o que mudou ou sumiu da cópia gravada. Exemplo real da demonstração: na rodada 1, o `ext_14` estava `confirmed`; depois da correção da ingestão, ele é `pending`, como no extrato, e por isso vai para o próximo fechamento. Lista vazia com entrada mudada quer dizer que entrou dado novo.
- **Decisão.** Com a mesma entrada, roda a regra de hoje e compara item a item com o gravado. Uma diferença ali é regressão ou correção da regra, e vira issue.

## 5. Por que a regra decidiu assim

A regra fica em `backend/src/fechamento/`, como funções puras. O motivo de cada pendência está no `GLOSSARY.md`, e os grupos e a chave fraca, na ADR 0002. Para isolar um caso, monte um teste em `backend/tests/` com os construtores de `tests/construtores.py` (`recebivel`, `lancamento`, `CORTE`), copiando os valores do passo 3. Ele roda em milissegundos, sem banco nem fila, e fica como teste de regressão.

## 6. O fechamento não rodou

- `GET /operacao` (só o suporte, pelo mesmo `/api/docs`) mostra a saúde da fila:
  - `pedidos_parados` e `idade_do_mais_antigo_segundos`: ingestões gravadas que o relay do outbox ainda não publicou. O relay roda a cada 10 segundos; um pedido parado há minutos quer dizer beat ou worker fora do ar.
  - `mensagens_na_dead_letter`: fechamentos que falharam de vez, na fila `fechamento.morta`. `null` quer dizer que a api não alcançou o RabbitMQ.
- `docker compose logs worker | grep "dead letter"` mostra cada falha definitiva com a tarefa, o cliente, o corte e o erro. Ela só volta na próxima ingestão, até 6 horas depois, ou com um reprocessamento pelo suporte (ADR 0004). O processo que morre por falta de memória chega à fila morta sem essa linha: aparece só na contagem da `/operacao`. As mensagens ficam no painel do RabbitMQ (`http://localhost:15672`).
- `docker compose logs worker | grep "rodada "` mostra cada rodada com cliente, corte, versão e se é **nova** ou **existente**. Existente quer dizer que a entrada é igual à de uma rodada que já existe, e o pedido devolveu essa rodada.
