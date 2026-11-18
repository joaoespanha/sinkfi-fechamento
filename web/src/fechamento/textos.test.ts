// Os textos que dependem da regra: o que a tela diz precisa bater com o que o backend fez.
import { describe, expect, it } from 'vitest'
import {
  acharItem,
  avisoDaConfirmacao,
  chaveDoItem,
  fraseDoConferido,
  podeConferir,
  podeResolver,
  fraseDaResolucao,
  fraseDaFaixa,
  fraseDaConferencia,
  type Item,
  linhaDaAtualizacao,
  linhaDoResumo,
  mudancaDaConferencia,
  textoDaChave,
  type Conferencia,
  textoDoAviso,
} from './textos'

/** Um grupo com um recebível de NSU `nsu`, pago por um crédito com a descrição `descricao`. */
function casado(nsu: string, descricao: string): Item {
  return {
    recebiveis: [
      {
        id: 'r1',
        loja_id: 'loja',
        adquirente: 'stone',
        trilho: 'card',
        vendido_em: '2026-11-01',
        liquidacao_prevista: '2026-11-09',
        liquido_centavos: 10000,
        nsu,
        parcela: 1,
        parcelas: 1,
        status: 'open',
      },
    ],
    creditos: [
      {
        id: 'c1',
        transacao_id: 'T1',
        transacao_original_id: null,
        lancado_em: '2026-11-09T13:00:00Z',
        valor_centavos: 10000,
        documento_contraparte: '16501555000100',
        descricao,
        tipo: 'settlement',
        status: 'confirmed',
      },
    ],
    esperado_centavos: 10000,
    caiu_centavos: 10000,
    nao_caiu_centavos: 0,
    proximo_fechamento_centavos: 0,
    severidade: null,
    motivo: null,
    pendencia_centavos: null,
    resolucao: null,
    dia: '2026-11-09',
  }
}

describe('textoDaChave', () => {
  it('NSU inteiro na descrição é chave forte', () => {
    expect(textoDaChave(casado('STN-1', 'STN-1 novembro'))).toMatch(/chave forte/)
  })

  it('NSU dentro de outro NSU não é chave forte', () => {
    // A regra não lê "STN-12" como a venda STN-1: se casou, foi pela chave fraca.
    expect(textoDaChave(casado('STN-1', 'STN-12'))).toMatch(/chave fraca/)
  })
})

describe('endereço do item', () => {
  it('o mesmo id em duas adquirentes abre o item de cada uma', () => {
    // O id do recebível vem da adquirente: a Stone e a PagSeguro podem usar o mesmo (ADR 0009).
    const daStone = casado('STN-1', 'STN-1')
    const base = casado('PAG-1', 'PAG-1')
    const daPagseguro: Item = { ...base, recebiveis: [{ ...base.recebiveis[0], adquirente: 'pagseguro' }] }

    expect(chaveDoItem(daStone)).not.toBe(chaveDoItem(daPagseguro))
    expect(acharItem([daStone, daPagseguro], chaveDoItem(daPagseguro))).toBe(daPagseguro)
  })
})

// A faixa do suporte: os mesmos textos servem à lojista e ao suporte, então não falam com "você" sobre o fechamento.

describe('textos de estado sem pronome', () => {
  // O Intl põe espaço não separável depois do "R$".
  const resumo = {
    falta_de_verdade_centavos: 730_000,
    itens_falta_de_verdade: 2,
    itens_para_conferir: 0,
    limite_trava_centavos: 500_000,
  }

  it('o resumo acima da trava diz o limite sem "seu"', () => {
    expect(linhaDoResumo({ ...resumo, recomendacao: 'nao_feche' })).toBe(
      'Não feche: faltam R$\u00a07.300,00, acima do limite de R$\u00a05.000,00',
    )
  })

  it('o resumo dentro da trava diz o limite sem "seu"', () => {
    expect(linhaDoResumo({ ...resumo, recomendacao: 'pode_fechar', limite_trava_centavos: 1_000_000 })).toBe(
      'Pode fechar: faltam R$\u00a07.300,00, dentro do limite de R$\u00a010.000,00',
    )
  })

  it('o aviso de fechamento anterior não diz "você"', () => {
    const semana = {
      semana: '2026-11-10',
      corte: '2026-11-10T21:00:00Z',
      atual: false,
      tem_rodada: true,
      itens_falta_de_verdade: 1,
      itens_para_conferir: 2,
      conferido: false,
      aviso: true,
    }
    expect(textoDoAviso(semana)).toBe('O fechamento de 10/11 ainda não foi conferido: 1 falta de verdade, 2 para conferir.')
  })
})

describe('faixa do suporte', () => {
  it('diz que o suporte vê o que o cliente vê', () => {
    expect(fraseDaFaixa('Marina')).toBe('Você está vendo o fechamento como Marina vê.')
  })

  const conferencia = (rodada_id: number): Conferencia => ({
    quem: 'marina@sinkfi.demo',
    em: '2026-11-17T21:02:00Z',
    rodada_id,
    limite_trava_centavos: null,
    resumo: {
      recomendacao: 'pode_fechar',
      falta_de_verdade_centavos: 0,
      itens_falta_de_verdade: 0,
      itens_para_conferir: 0,
      limite_trava_centavos: null,
    },
  })

  it('sem conferência, diz que ninguém conferiu', () => {
    expect(fraseDaConferencia(null, 12)).toBe('Ninguém conferiu este fechamento ainda.')
  })

  it('com conferência na rodada mostrada, diz quem e quando', () => {
    expect(fraseDaConferencia(conferencia(12), 12)).toBe('marina@sinkfi.demo conferiu em 17/11/2026, 18:02, nesta rodada.')
  })

  it('com conferência numa rodada anterior, diz as duas rodadas', () => {
    expect(fraseDaConferencia(conferencia(11), 12)).toBe(
      'marina@sinkfi.demo conferiu em 17/11/2026, 18:02, na rodada 11. Esta é a rodada 12.',
    )
  })
})

// A conferência (ADR 0012): o botão some quando ela já vale para o que a tela mostra, e a confirmação diz o que não muda.
describe('conferência', () => {
  const resumo = {
    recomendacao: 'nao_feche' as const,
    falta_de_verdade_centavos: 1_085_933,
    itens_falta_de_verdade: 3,
    itens_para_conferir: 2,
    limite_trava_centavos: 500_000,
  }
  const conferida = (rodada_id: number, r = resumo): Conferencia => ({
    quem: 'marina@sinkfi.demo',
    em: '2026-11-17T21:02:00Z',
    rodada_id,
    limite_trava_centavos: r.limite_trava_centavos,
    resumo: r,
  })

  it('sem conferência, dá para conferir', () => {
    expect(podeConferir(null, 12, resumo)).toBe(true)
  })

  it('conferida nesta rodada com o mesmo resumo, não dá para conferir de novo', () => {
    expect(podeConferir(conferida(12), 12, { ...resumo })).toBe(false)
  })

  it('conferida nesta rodada, mas o limite mudou o resumo, dá para conferir de novo', () => {
    const outroLimite = { ...resumo, recomendacao: 'pode_fechar' as const, limite_trava_centavos: 2_000_000 }
    expect(podeConferir(conferida(12), 12, outroLimite)).toBe(true)
  })

  it('conferida numa rodada anterior, dá para conferir de novo', () => {
    expect(podeConferir(conferida(11), 12, resumo)).toBe(true)
  })

  it('o estado diz quem conferiu e quando', () => {
    expect(fraseDoConferido(conferida(12))).toBe('Conferido por marina@sinkfi.demo em 17/11/2026, 18:02')
  })

  it('a confirmação diz que os itens para conferir continuam', () => {
    expect(avisoDaConfirmacao(resumo)).toBe('Os 2 itens para conferir continuam na lista. Nada trava.')
  })

  it('a confirmação com um item para conferir fica no singular', () => {
    expect(avisoDaConfirmacao({ ...resumo, itens_para_conferir: 1 })).toBe(
      'O item para conferir continua na lista. Nada trava.',
    )
  })

  it('a confirmação sem itens para conferir só diz que nada trava', () => {
    expect(avisoDaConfirmacao({ ...resumo, itens_para_conferir: 0 })).toBe('Nada trava.')
  })
})

// O aviso da conferência que já não vale: precisa mostrar o que mudou, e não duas linhas iguais.
describe('aviso da conferência', () => {
  const resumo = {
    recomendacao: 'faltam' as const,
    falta_de_verdade_centavos: 1_085_933,
    itens_falta_de_verdade: 5,
    itens_para_conferir: 2,
    limite_trava_centavos: null,
  }
  const conferida = (rodada_id: number, r: typeof resumo | Conferencia['resumo'] = resumo): Conferencia => ({
    quem: 'marina@sinkfi.demo',
    em: '2026-11-17T21:02:00Z',
    rodada_id,
    limite_trava_centavos: r.limite_trava_centavos,
    resumo: r,
  })

  it('quando só a contagem para conferir mudou, antes e agora dizem a contagem', () => {
    expect(mudancaDaConferencia(conferida(12, { ...resumo, itens_para_conferir: 1 }), 12, resumo)).toEqual({
      antes: 'Faltam R$\u00a010.859,33 em 5 itens · 1 item para conferir',
      agora: 'Faltam R$\u00a010.859,33 em 5 itens · 2 itens para conferir',
    })
  })

  it('sem itens para conferir, a linha é só a do resumo', () => {
    const antes = conferida(12, { ...resumo, itens_para_conferir: 1 })
    expect(mudancaDaConferencia(antes, 12, { ...resumo, itens_para_conferir: 0 })).toEqual({
      antes: 'Faltam R$\u00a010.859,33 em 5 itens · 1 item para conferir',
      agora: 'Faltam R$\u00a010.859,33 em 5 itens',
    })
  })

  it('rodada nova com o mesmo resumo diz que recalculou, em vez de repetir a linha', () => {
    expect(mudancaDaConferencia(conferida(11), 12, { ...resumo })).toEqual({
      mesmoResumo:
        'O fechamento foi recalculado, e o resumo continua o mesmo: Faltam R$\u00a010.859,33 em 5 itens · 2 itens para conferir.',
    })
  })

  it('o limite mudou sem mudar a linha, e o aviso diz isso', () => {
    const semFalta = {
      ...resumo,
      recomendacao: 'pode_fechar' as const,
      falta_de_verdade_centavos: 0,
      itens_falta_de_verdade: 0,
    }
    expect(mudancaDaConferencia(conferida(12, { ...semFalta, limite_trava_centavos: 500_000 }), 12, semFalta)).toEqual({
      mesmoResumo: 'O limite da trava mudou, e o resumo continua o mesmo: Pode fechar · 2 itens para conferir.',
    })
  })
})

// A agenda é 0, 6, 12 e 18h UTC: 21h, 3h, 9h e 15h em São Paulo (ADR 0011).
describe('linha da atualização', () => {
  const nada = { ultima_em: null, atrasada: false, primeira_perdida_em: null }

  it('próxima no mesmo dia da última mostra só a hora', () => {
    expect(
      linhaDaAtualizacao({ ...nada, ultima_em: '2026-11-18T18:00:05Z', proxima_prevista_em: '2026-11-19T00:00:00Z' }),
    ).toBe('Dados atualizados em 18/11, 15:00 · próxima atualização prevista às 21:00')
  })

  it('próxima no dia seguinte mostra o dia', () => {
    expect(
      linhaDaAtualizacao({ ...nada, ultima_em: '2026-11-19T00:00:05Z', proxima_prevista_em: '2026-11-19T06:00:00Z' }),
    ).toBe('Dados atualizados em 18/11, 21:00 · próxima atualização prevista 19/11 às 03:00')
  })

  it('atrasada nomeia a primeira atualização que não aconteceu', () => {
    expect(
      linhaDaAtualizacao({
        ultima_em: '2026-11-17T18:00:05Z',
        proxima_prevista_em: '2026-11-18T12:00:00Z',
        atrasada: true,
        primeira_perdida_em: '2026-11-18T00:00:00Z',
      }),
    ).toBe(
      'Dados de 17/11, 15:00 · a atualização prevista para 17/11 às 21:00 não aconteceu · próxima prevista 18/11 às 09:00',
    )
  })

  it('sem ingestão diz que ainda não houve atualização', () => {
    // Sem a última para comparar o dia, a próxima vai sempre com o dia.
    expect(linhaDaAtualizacao({ ...nada, proxima_prevista_em: '2026-11-19T00:00:00Z' })).toBe(
      'Ainda sem atualização · primeira prevista 18/11 às 21:00',
    )
  })
})

describe('resolução (ADR 0014)', () => {
  const credito = (campos: Partial<Item>): Item => ({
    ...casado('1', 'PIX RECEBIDO'),
    recebiveis: [],
    esperado_centavos: null,
    caiu_centavos: null,
    nao_caiu_centavos: null,
    proximo_fechamento_centavos: null,
    severidade: 'para_conferir',
    motivo: 'entrada_sem_recebivel',
    pendencia_centavos: 10000,
    ...campos,
  })

  it('só a pendência para conferir pode ser resolvida', () => {
    expect(podeResolver(credito({}))).toBe(true)
    expect(podeResolver(credito({ motivo: 'pode_ser_antecipacao' }))).toBe(true)
    expect(podeResolver(credito({ severidade: 'falta_de_verdade', motivo: 'venda_cancelada' }))).toBe(false)
    expect(podeResolver(credito({ severidade: null, motivo: null, pendencia_centavos: null }))).toBe(false)
    // Grupo com recebível: a resolução é presa ao lançamento, então o grupo fica de fora.
    expect(podeResolver({ ...credito({}), recebiveis: casado('1', 'x').recebiveis })).toBe(false)
    expect(podeResolver(credito({ resolucao: { quem: 'a@b.c', em: '2026-11-10T15:00:00Z', nota: 'x' } }))).toBe(false)
  })

  it('a frase diz quem resolveu e quando', () => {
    expect(fraseDaResolucao({ quem: 'marina@loja.com', em: '2026-11-10T15:00:00Z', nota: 'aporte' })).toBe(
      'Resolvida por marina@loja.com em 10/11/2026, 12:00',
    )
  })
})
