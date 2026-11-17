# Fechamento semanal

A conferência que a lojista faz uma vez por semana, no dia do seu corte (a Marina fecha na segunda à noite): o que as adquirentes deviam ter depositado até o corte, o que caiu de fato na conta e o que falta de verdade. Vale para todas as lojas da mesma conta.

## Partes

**Adquirente**:
Empresa que captura a venda (cartão ou Pix) e repassa o dinheiro para a conta da lojista. Nos dados, Stone e PagSeguro. É reconhecida pelo documento da contraparte, nunca pelo nome.
_Evitar_: maquininha, credenciadora

**Loja**:
Ponto de venda da lojista. Várias lojas podem receber na mesma conta e pela mesma adquirente.
_Evitar_: estabelecimento, filial

**Cliente**:
A empresa que contrata a sinkfi, com todas as suas lojas e a conta em que elas recebem. Um fechamento é sempre de um cliente.
_Evitar_: conta, tenant, empresa

**Lojista**:
A pessoa do cliente que faz o fechamento. Vê só o próprio cliente e é quem define a trava.
_Evitar_: usuário, dona

**Suporte**:
A pessoa do time da sinkfi que investiga um fechamento. Vê qualquer cliente e pode pedir uma rodada nova.
_Evitar_: admin, operador

## O que deveria cair

**Recebível**:
Valor líquido que uma adquirente deve depositar por uma venda ou por uma parcela dela, numa data prevista.
_Evitar_: venda, transação, agenda

**Liquidação prevista**:
Data em que a adquirente diz que o recebível vai cair na conta. Um recebível está **vencido** quando essa data já passou.
_Evitar_: vencimento, data de pagamento

**NSU**:
Código que a adquirente dá a uma venda. Ele se repete em todas as parcelas da mesma venda, então sozinho não identifica uma parcela.
_Evitar_: código da transação, ID da venda

**Parcela**:
Cada recebível de uma venda parcelada. Uma venda à vista tem um único recebível, sem parcela.

**Venda cancelada**:
Venda desfeita. O recebível dela não é esperado, e o dinheiro que cair por ela deve voltar para a adquirente.

## O que caiu na conta

**Lançamento**:
Uma linha do extrato da conta, lida pelo Open Finance. Lançamentos repetidos com a mesma transação são um só.
_Evitar_: transação, movimento

**Crédito**:
Lançamento de entrada que pode pagar um recebível: repasse da adquirente ou Pix recebido. Tarifa da conta e transferência da própria titular não são crédito.
_Evitar_: depósito, entrada

**Chargeback**:
Lançamento de saída que desfaz um crédito já casado. O dinheiro daquele recebível saiu da conta.
_Evitar_: estorno, contestação

## Casamento

**Casamento**:
A ligação entre um crédito e o recebível, ou o grupo de recebíveis, que ele paga. Não leva em conta o corte.
_Evitar_: match, conciliação

**Chave forte**:
Casamento pelo NSU citado na descrição do crédito, desde que o crédito venha da adquirente do recebível, ou seja Pix quando o recebível é Pix.

**Chave fraca**:
Casamento de um crédito sem NSU por mesma adquirente e mesmo valor líquido, dentro da janela da chave fraca. Só vale para valor exato.

**Janela da chave fraca**:
Intervalo, em dias corridos em torno da liquidação prevista, em que um crédito pode casar pela chave fraca. Fora dele, o crédito não casa.

**Grupo de recebíveis**:
A unidade de resultado do fechamento: um ou mais recebíveis e os créditos casados com eles. Quando um crédito serve para mais de um recebível, eles ficam juntos num grupo só, sem escolher qual foi pago. Todo recebível esperado está em exatamente um grupo.
_Evitar_: status do recebível, linha

**Entre lojas**:
Grupo cujos recebíveis são de lojas diferentes da mesma adquirente, quando o crédito não diz de qual loja é.

## Fechamento

**Fechamento**:
A conferência de uma semana de um cliente, com o que caiu até o corte. A Marina fecha na segunda à noite.
_Evitar_: conciliação, fechar o caixa

**Corte**:
O momento que separa um fechamento do seguinte. Cada cliente tem o seu dia, hora e fuso; o da Marina é segunda às 18:00, horário de São Paulo.
_Evitar_: horário limite, deadline

**Fechamento atual**:
O fechamento mais recente cujo corte já passou e que tem algum recebível previsto ou crédito nos seus dias. É onde a tela abre; os anteriores ficam para consulta.
_Evitar_: semana padrão, semana vigente, semana atual

**Rodada**:
Um cálculo do fechamento de um cliente com os dados que havia naquele momento. Não muda depois de gravada: dados novos geram outra rodada, e a lojista vê a mais recente do fechamento que escolheu.
_Evitar_: execução, versão, reprocessamento

**Versão da regra**:
A versão do cálculo que gerou uma rodada. Corrigir a regra gera rodadas novas e nunca muda as antigas. Não confundir com rodada, que é um cálculo e não uma versão.
_Evitar_: release

**Esperado**:
A soma dos recebíveis com liquidação prevista até o dia do fechamento. Esperado = Caiu + Não caiu + Próximo fechamento.

**Caiu**:
A parte do esperado que entrou na conta até o corte e não foi desfeita por chargeback.
_Evitar_: entrou, já caiu, recebido

**Não caiu**:
A parte do esperado que não está na conta: não foi depositada, foi depositada em parte ou saiu por chargeback.
_Evitar_: falta, faltante, em aberto

**Próximo fechamento**:
A parte do esperado cujo crédito casou, mas caiu depois do corte. Não é pendência: entra no fechamento seguinte.
_Evitar_: atrasado, vai cair

**A vencer**:
Recebível com liquidação prevista depois do dia do fechamento. Fica fora do esperado.
_Evitar_: futuro, vai cair

**Entrada sem recebível**:
Crédito que não casa com nenhum recebível.
_Evitar_: crédito órfão, sobra

## Pendências e resumo

**Pendência**:
Um grupo de recebíveis ou um lançamento que pede atenção da lojista no fechamento. Cada pendência tem uma severidade e o motivo.
_Evitar_: divergência, erro, alerta

**Falta de verdade**:
Severidade da pendência cujo dinheiro muda o fechamento: o dinheiro não entrou, ou entrou e não é da lojista. A soma das faltas de verdade é absoluta, sem compensar uma sobra com uma falta.
_Evitar_: divergência crítica, erro

**Para conferir**:
Severidade da pendência que vale olhar mas não muda o fechamento, como uma entrada sem recebível.
_Evitar_: aviso, divergência leve

**Resumo**:
A linha no topo do fechamento que diz se a lojista pode fechar e, quando não pode, quanto soma a falta de verdade e em quantos itens.
_Evitar_: veredito, status

**Trava**:
Limite opcional que a lojista define sobre a soma das faltas de verdade. Acima dele, o resumo recomenda não fechar. Ela só muda o resumo e nunca impede o fechamento. Vem desligada.
_Evitar_: bloqueio, materialidade

**Término**:
O registro de que a lojista terminou um fechamento: quem, quando, qual rodada viu e o resumo daquele momento. Não trava nada, e ela pode registrar de novo se o fechamento mudar. Na tela, o botão "Terminei".
_Evitar_: fechar, concluir, fechamento concluído
