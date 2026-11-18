# O suporte acha o cliente por e-mail, CNPJ ou nome

Status: aceito, 18/11/2026

O suporte abre um cliente por um campo de busca que procura no e-mail das lojistas, no CNPJ das lojas e no nome do cliente e das lojas. Antes era preciso digitar o id interno (`cli_marina`), que nem o suporte nem quem avalia conhece. O que chega num chamado é o e-mail de quem escreveu, o nome do cliente ou o CNPJ.

O ADR 0005 dá ao suporte acesso a qualquer cliente, mas não diz como ele chega a um. A tela só com o id foi um corte de escopo que nunca foi registrado.

## Decisão

- **Rota:** `GET /clientes?busca=<termo>`, só para o papel suporte. A lojista recebe 403, e quem está sem sessão recebe 401, como nas rotas de operação. A rota não tem cliente no endereço, então não passa pelo ponto único de checagem do ADR 0005. A barreira dela é o papel.
- **Onde procura:** o e-mail das lojistas (o suporte não tem cliente e não aparece), o documento das lojas, o nome do cliente e o nome das lojas.
- **Como casa:** por pedaço do texto e sem diferenciar maiúscula (`marina` acha `Marina` e `marina@sinkfi.demo`). Para o CNPJ, a busca tira do termo tudo que não for dígito, então aceita o número com ou sem pontuação. Se sobrarem menos de 3 dígitos, o CNPJ fica de fora da busca, senão `ab12` casaria com quase todo documento.
- **Termo mínimo de 3 caracteres**, contados depois de tirar os espaços das pontas. Com menos, a resposta é 422.
- **Uma linha por cliente, no máximo 10**, em ordem de nome. Cada linha traz o id, o nome do cliente e as lojas, com nome e CNPJ. Duas lojas com o mesmo CNPJ, como as da Marina, dão um resultado só.
- **Tela:** um campo "E-mail, CNPJ ou nome" e a lista de resultados embaixo. Um clique abre o cliente.

## Alternativas recusadas

- **Manter o id digitado.** Supõe um sistema de chamados que entregue o id ao suporte, e esse sistema não existe aqui. Quem testa trava na primeira tela.
- **Um seletor com todos os clientes.** Não escala e mostra todos os clientes de uma vez para quem só precisa de um.
- **A lojista mostrar um "código do cliente".** Põe a fricção em quem pede ajuda, e a lojista não é técnica.

## Consequências

- **Acento conta.** `sao` não acha `São`. Ignorar acento pede a extensão `unaccent` do Postgres e uma migração, o que fica para quando houver nome com acento nos dados.
- **Sem índice para a busca.** O `ILIKE '%termo%'` percorre as tabelas inteiras. Com poucos clientes isso não pesa; com muitos, o caminho é um índice trigram (`pg_trgm`).
- **Um termo só com dígitos casa em qualquer campo.** `104` acha o CNPJ `10493827000160` e também um e-mail ou nome que tenha `104`. Como o resultado é por cliente, isso só aumenta a lista.
- **Termo comum demais corta resultados.** Acima de 10 clientes, o suporte precisa de um termo mais específico. A tela avisa quando a lista veio cheia.
- **O mínimo e o limite estão nos dois lados.** O web repete o 3 e o 10 da api para não chamar à toa e para saber que a lista veio cheia. O contrato gera só tipos, então mudar um lado exige mudar o outro.
- **O CNPJ precisa estar gravado só com dígitos.** A ingestão grava o documento como vem no CSV, e os dados de hoje vêm só com dígitos. Um CSV com o CNPJ pontuado não seria achado pelo número; a correção é normalizar na ingestão.

## Depois de achar o cliente

O suporte vê **a mesma tela da lojista**: num chamado, os dois olham a mesma coisa. Por cima dela fica uma faixa só do suporte, que traz:

- "Você está vendo o fechamento como <cliente> vê";
- a conferência vista de fora (ADR 0012), com o e-mail de quem marcou, quando e em qual rodada, ou "Ninguém conferiu este fechamento ainda";
- o botão **Pedir rodada nova**, que chama `POST /clientes/{id}/reprocessar` para a semana mostrada.

O pedido vai para a fila. A tela avisa "Pedido enviado" e recarrega uma vez depois de 5 s. Ela não espera a rodada chegar: sem entrada nova, o hash é o mesmo e a rodada que volta é a mesma (ADR 0007), então não há o que esperar.

Os textos de estado que o suporte também lê ficaram sem pronome, para a lojista e para o suporte: "acima do limite de R$ …", "O fechamento de 10/11 ainda não foi conferido" e "mudou desde a última conferência". O "?" dos termos e o "o que fazer" de cada item continuam falando com a lojista. São instruções que o suporte repassa no chamado.

Ficam fora, como corte de escopo:
- **o histórico de rodadas na tela**: `GET /rodadas` existe, e a investigação usa `python -m sinkfi.reproduzir`;
- **um painel de `GET /operacao`**.

## Testes que garantem

- `suporte_acha_o_cliente_pelo_email_da_lojista`
- `suporte_acha_o_cliente_pelo_cnpj_com_ou_sem_pontuacao`
- `suporte_acha_o_cliente_pelo_nome`
- `suporte_nao_aparece_na_busca`
- `busca_devolve_so_o_cliente_que_bate`
- `lojas_com_o_mesmo_cnpj_dao_um_resultado_so`
- `busca_devolve_no_maximo_10_em_ordem_de_nome`
- `termo_curto_devolve_422`
- `lojista_nao_busca_clientes`
- `busca_sem_token_devolve_401`
- `textos.test.ts`: `faixa do suporte` e `textos de estado sem pronome`
