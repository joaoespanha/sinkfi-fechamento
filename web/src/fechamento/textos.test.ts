// Os textos que dependem da regra: o que a tela diz precisa bater com o que o backend fez.
import { describe, expect, it } from 'vitest'
import {
  acharItem,
  chaveDoItem,
  fraseDaFaixa,
  fraseDoTermino,
  type Item,
  linhaDaAtualizacao,
  linhaDoResumo,
  textoDaChave,
  type Termino,
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
      terminado: false,
      aviso: true,
    }
    expect(textoDoAviso(semana)).toBe('O fechamento de 10/11 ainda não foi terminado: 1 falta de verdade, 2 para conferir.')
  })
})

describe('faixa do suporte', () => {
  it('diz que o suporte vê o que o cliente vê', () => {
    expect(fraseDaFaixa('Marina')).toBe('Você está vendo o fechamento como Marina vê.')
  })

  const termino = (rodada_id: number): Termino => ({
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

  it('sem "Terminei", diz que ninguém terminou', () => {
    expect(fraseDoTermino(null, 12)).toBe('Ninguém terminou este fechamento ainda.')
  })

  it('com "Terminei" na rodada mostrada, diz quem e quando', () => {
    expect(fraseDoTermino(termino(12), 12)).toBe('marina@sinkfi.demo terminou em 17/11/2026, 18:02, nesta rodada.')
  })

  it('com "Terminei" numa rodada anterior, diz as duas rodadas', () => {
    expect(fraseDoTermino(termino(11), 12)).toBe(
      'marina@sinkfi.demo terminou em 17/11/2026, 18:02, na rodada 11. Esta é a rodada 12.',
    )
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
