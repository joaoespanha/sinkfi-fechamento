# Login próprio, dois papéis e um ponto único de checagem

Status: aceito, 17/11/2026

A `api` faz o próprio login e decide o acesso por dois papéis: a lojista vê só o cliente dela, e o suporte vê qualquer cliente. A comparação entre o cliente do endereço e o do usuário acontece num ponto único, por onde toda rota passa. Escolhemos o login próprio porque o que pesa aqui é a autorização entre clientes, e ela é a mesma com ou sem um serviço de identidade.

## Decisão

| Ação | Lojista | Suporte |
| --- | --- | --- |
| Ver o fechamento e a explicação | Só do próprio cliente | De qualquer cliente |
| Mudar o limite da trava | Sim | Não |
| Pedir reprocessamento | Não | Sim |
| Marcar "Terminei" | Sim | Não |

- Cada lojista pertence a um cliente. O suporte não pertence a nenhum.
- A senha é guardada com hash (argon2). O login devolve um token JWT em cookie `httpOnly` com `SameSite=Strict`, válido por 8 horas, sem renovação.
- O token carrega só a identidade. O papel e o cliente são lidos do banco a cada requisição.
- O cliente fica no endereço (`/clientes/{id}/...`), porque o suporte precisa escolher qual abrir.
- Pedir um cliente que não é o seu devolve 404, não 403.
- O nginx do `web` serve a tela, repassa `/api` e limita as requisições por IP, com um limite mais apertado no login.
- Os usuários nascem por seed. `worker`, `beat` e ingestão não fazem login: falam com o Postgres e o RabbitMQ pela rede interna.

## Alternativas recusadas

- **Serviço de identidade (Keycloak).** É o caminho com mais de um produto ou login corporativo. Aqui seria um container pesado a mais e outro ponto de falha na subida, sem mudar a autorização.
- **Token no `localStorage`.** Qualquer script na página lê o token. O cookie `httpOnly` não impede a injeção de script, mas impede que o token seja levado embora.
- **Cliente tirado só do token (`/meu/fechamento`).** É mais difícil de errar para a lojista, mas não serve ao suporte, e exigiria dois conjuntos de rotas.
- **Token curto com renovação.** Existe porque um JWT normalmente não pode ser cancelado. O nosso pode, pela leitura do usuário no banco a cada requisição.
- **Bloqueio progressivo da conta agora** (5 minutos, 5 horas, bloqueio). É o passo seguinte ao limite por IP. Fica de fora porque exige um caminho de liberação e permite trancar a lojista para fora de propósito.

## Consequências

- Tirar um acesso vale na hora, ao custo de uma consulta ao banco por requisição.
- A tela e a `api` respondem no mesmo endereço, então a `api` não habilita CORS.
- O limite por IP vive na memória de cada nginx e não segura um ataque distribuído contra uma conta só.
- Depois de 8 horas a lojista faz login de novo.
- Uma rota nova que não passe pelo ponto único de checagem vaza dados entre clientes. O teste de isolamento precisa cobrir toda rota com cliente no endereço.

## Testes que garantem

- `lojista_nao_ve_fechamento_de_outro_cliente`
- `suporte_ve_qualquer_cliente`
- `lojista_nao_reprocessa`
- `suporte_nao_muda_o_limite`
- `suporte_nao_marca_terminei`
- `rota_sem_token_devolve_401`
- `usuario_inativo_perde_o_acesso_com_token_valido`
