# O suporte acha o cliente por e-mail, CNPJ ou nome

Status: aceito, 18/11/2026

O suporte abre um cliente por um campo de busca que procura no e-mail das lojistas, no CNPJ das lojas e no nome do cliente e das lojas. Antes era preciso digitar o id interno (`cli_marina`), que nem o suporte nem quem avalia conhece. O que chega num chamado é o e-mail de quem escreveu, o nome da empresa ou o CNPJ.

O ADR 0005 dá ao suporte acesso a qualquer cliente, mas não diz como ele chega a um. A tela só com o id foi um corte de escopo que nunca foi registrado.

## Decisão

- **Rota:** `GET /clientes?busca=<termo>`, só para o papel suporte. A lojista recebe 403, e quem está sem sessão recebe 401, como nas rotas de operação. A rota não tem cliente no endereço, então não passa pelo ponto único de checagem do ADR 0005. A barreira dela é o papel.
- **Onde procura:** o e-mail dos usuários com cliente (o suporte não tem cliente e não aparece), o documento das lojas, o nome do cliente e o nome das lojas.
- **Como casa:** por pedaço do texto e sem diferenciar maiúscula (`marina` acha `Marina` e `marina@sinkfi.demo`). Para o CNPJ, a busca tira do termo tudo que não for dígito, então aceita o número com ou sem pontuação.
- **Termo mínimo de 3 caracteres**, contados depois de tirar os espaços. Com menos, a resposta é 422.
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

## Testes que garantem

- `suporte_acha_o_cliente_pelo_email_da_lojista`
- `suporte_acha_o_cliente_pelo_cnpj_com_ou_sem_pontuacao`
- `suporte_acha_o_cliente_pelo_nome`
- `busca_devolve_so_o_cliente_que_bate`
- `lojas_com_o_mesmo_cnpj_dao_um_resultado_so`
- `busca_devolve_no_maximo_10`
- `termo_curto_devolve_422`
- `lojista_nao_busca_clientes`
- `busca_sem_token_devolve_401`
