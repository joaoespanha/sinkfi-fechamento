// Os textos que dependem da regra: o que a tela diz precisa bater com o que o backend fez.
import { describe, expect, it } from 'vitest'
import { type Item, textoDaChave } from './textos'

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
