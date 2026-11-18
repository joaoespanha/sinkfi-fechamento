# Conferência no lugar do "Terminei"

Status: aceito, 18/11/2026

O sinal de que a lojista acabou de olhar o fechamento continua sendo um registro que não trava nada (ADR 0003), mas deixa de se chamar "Terminei". O termo passa a ser **Conferência**, e na tela o botão diz "Marcar como conferido". O nome muda em tudo: GLOSSARY, tela, rota, contrato da API, código e tabela. Escolhemos assim porque "Terminei" não dizia o que fica gravado, e porque um glossário que fala uma língua e um código que fala outra confundem quem chega depois.

## Contexto

O botão "Terminei" (ADR 0003 e 0007, `DECISOES.md`, Monitorar) grava quem, quando, a rodada vista e o resumo daquele momento. Na tela, o nome soava como um fechamento, e a lojista não tinha como saber que nada fica travado nem o que exatamente foi registrado.

## Decisões

- **Continua um registro, não um fechamento.** Um "fechar" de verdade pediria uma política para o dado bancário que chega depois (ADR 0007) e para quem reabre a semana, e ninguém a definiu. O fechamento contábil da lojista acontece no ERP dela.
- **"Conferido" convive com "Para conferir".** A severidade de pendência mantém o nome. Conferir o fechamento inclui olhar esses itens, e a conferência não os resolve. A tela tem de deixar isso claro.
- **Confirmação antes de registrar.** Um `<dialog>` modal mostra o resumo que vai ficar gravado e diz que os itens para conferir continuam na lista e que nada trava. Cancelar e Esc não gravam nada. A confirmação dentro do próprio cartão foi recusada porque deixava o resumo menos explícito.
- **Depois de conferir, o botão vira estado.** "Conferido por … em …" fica no cartão, no lugar do botão, enquanto a conferência valer para o que a tela mostra: a mesma rodada e o mesmo resumo. Com rodada nova, ou quando o limite muda o resumo (o limite é lido na hora, ADR 0006), o botão volta e o topo mostra o antes e o agora. A linha neutra "X conferiu este fechamento" saiu do topo, porque repetia o estado.
- **A regra mora na tela.** A API continua aceitando uma conferência repetida: recusar com 409 exigiria comparar resumos no backend, e o registro repetido não faz mal (é só inserção).
- **A troca vale em tudo.** A rota passa a ser `POST /clientes/{id}/conferencias`, a resposta do fechamento traz `ultima_conferencia`, a lista de fechamentos traz `conferido`, e a tabela `terminos` vira `conferencias` (migração 0008, só de nome, com os registros intactos).

## Alternativas recusadas

- **Criar uma ação de fechar.** É o que o ADR 0003 recusou, pelos mesmos motivos.
- **Renomear a severidade "Para conferir"** (por exemplo, para "Vale olhar"). Acaba com a colisão, mas troca um termo estável e já ensinado na tela por um menos natural.
- **Outra palavra no botão**, como "Marcar como revisado". Também evita a colisão, mas "conferir" é a palavra que a lojista usa para o que ela faz.
- **Trocar só a tela e os documentos.** Mais rápido, mas o GLOSSARY e o código passariam a falar línguas diferentes.

## Consequências

- Quem integrava com `POST /clientes/{id}/terminei` ou lia `ultimo_termino` precisa trocar. Hoje só a tela usa essa parte da API.
- Os ADRs anteriores e o `docs/debugar.md` passam a dizer "conferência". O `DECISOES.md` é prosa da autora e muda à parte.

## Testes que garantem

- `test_conferencia_grava_quem_quando_e_a_rodada_vista`
- `test_conferencia_de_novo_guarda_os_dois_registros`
- `test_suporte_nao_marca_conferido`
- `test_conferencia_no_fechamento_anterior_tira_ele_do_aviso`
- `sem conferência, diz que ninguém conferiu` (web)
- `conferida nesta rodada com o mesmo resumo, não dá para conferir de novo` (web)
- `conferida nesta rodada, mas o limite mudou o resumo, dá para conferir de novo` (web)
- `a confirmação diz que os itens para conferir continuam` (web)
