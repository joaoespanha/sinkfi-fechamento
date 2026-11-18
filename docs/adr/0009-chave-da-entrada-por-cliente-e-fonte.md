# Chave da entrada por cliente e por fonte: o recebível é a adquirente com o id

Status: aceito, 18/11/2026

Lojas, recebíveis e lançamentos passam a ter chave composta com o cliente, e o recebível também leva a adquirente: `lojas (cliente_id, id)`, `recebiveis (cliente_id, adquirente, id)`, `lancamentos (cliente_id, id)`. A regra, a reprodução, o hash da rodada e o endereço do item no web identificam o recebível por `(adquirente, id)`. Escolhemos assim porque cada id vem de fora e só é único dentro de quem o gerou, e uma chave mais larga que isso deixava um cliente sobrescrever o dado de outro.

## Contexto

A chave era só o `id`, e a ingestão grava com `ON CONFLICT (id) DO UPDATE`, sobrescrevendo todas as colunas, inclusive o `cliente_id`. Quando o cliente B mandava uma linha com um id que já era do A, a linha mudava de dono sem erro: o fechamento do A perdia dados e o do B mostrava os do A. A trava por cliente da ingestão não protege entre clientes.

Hoje só existe a Marina e não há upload: a fonte é uma pasta por cliente. As rodadas guardam cópia do que usaram (ADR 0006), então o histórico não foi corrompido. Mesmo assim, é a falha que um cliente novo transformaria em vazamento de dados entre empresas.

Quem gera cada id:

- **Loja**: o cadastro do cliente na sinkfi. Não há fonte externa.
- **Recebível**: a adquirente. A Stone e a PagSeguro numeram cada uma do seu jeito e podem repetir um id. O dado já traz a adquirente.
- **Lançamento**: o extrato da conta do cliente pelo Open Finance. Hoje cada cliente tem uma conta só.

## Decisões

- **Chave por cliente nas três tabelas, e pela adquirente no recebível.** O recebível ganha `cliente_id`, preenchido pela loja na migração, em vez de chegar ao cliente só pela loja.
- **A loja do recebível é do mesmo cliente.** A FK virou `(cliente_id, loja_id) → lojas (cliente_id, id)`. Um recebível que aponta para a loja de outro cliente derruba a ingestão do lote inteiro, em vez de ser ligado à loja errada.
- **A identidade do recebível é `(adquirente, id)` em todo o sistema, não só no banco.** Pôr a adquirente só na chave do banco deixaria entrar duas linhas que a regra misturaria num grupo só, sem erro. A regra usa `Recebivel.identidade`; a reprodução nomeia o recebível como `rec_1002 (stone)`; a busca de rodadas por recebível recebe a adquirente; o endereço do item no web é `<adquirente>:<id>`.
- **O hash da rodada desempata pela adquirente depois do id.** Entradas sem id repetido mantêm o mesmo hash, então a mudança não cria rodada nova para quem já tinha uma.
- **A versão da regra não sobe.** A regra só decide diferente quando duas adquirentes usam o mesmo id, uma entrada que o banco não aceitava antes. Para toda entrada possível até aqui, o resultado é o mesmo.

## Alternativas recusadas

- **Só um guarda na ingestão (recusar id que já é de outro cliente).** Fecha o vazamento, mas mantém o modelo dizendo que o id é global, e o próximo cliente com o mesmo id da Marina ficaria sem conseguir ingerir.
- **`(cliente_id, id)` também no recebível.** É o menor passo e fecha o vazamento entre clientes. Recusado porque o dado já traz a adquirente e o custo extra foi pequeno: o recebível do domínio já tinha a adquirente, e as cópias das rodadas também.
- **A fonte só no banco.** Os testes continuariam verdes com os dados atuais e o defeito apareceria no primeiro id repetido entre adquirentes.

## Consequências

- **Rotas antigas.** Um endereço de item salvo antes desta mudança, com o id puro, não abre mais o item.
- **Busca por NSU.** O NSU também é da adquirente, e a busca por NSU devolve as rodadas das duas quando ele se repete. Por ser uma busca, aceitamos.
- **Mais de uma conta por cliente.** Quando um cliente tiver mais de uma conta, o lançamento precisa da conta na chave e na identidade, como o recebível tem a adquirente.
- **Volta da migração.** O downgrade falha se já houver ids repetidos entre clientes ou adquirentes, porque voltar perderia dado.

## Testes que garantem

- `outro_cliente_com_os_mesmos_ids_nao_muda_a_entrada_da_marina`
- `recebivel_que_aponta_para_loja_de_outro_cliente_recusa_a_ingestao`
- `mesmo_id_em_duas_adquirentes_sao_dois_recebiveis`
- `busca_rodadas_pelo_recebivel_da_adquirente`
- `reproduzir_aponta_o_recebivel_da_adquirente_que_mudou`
- `hash_nao_depende_da_ordem_dos_recebiveis_com_o_mesmo_id`
- web: `o mesmo id em duas adquirentes abre o item de cada uma`
