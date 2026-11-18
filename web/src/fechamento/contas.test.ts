// As contas da interface (#32): o que os gráficos e os filtros mostram sai daqui.
import { describe, expect, it } from 'vitest'
import { SEM_FILTRO, adquirentes, pendencias, porDia, resolvidas, totais } from './contas'
import { ANTES, type Fechamento, type Item, dicaDoDia, emPorcento } from './textos'

let ids = 0

/** Um item mínimo: um recebível da adquirente, casado certo, salvo o que o caso mudar. */
function item(campos: Partial<Item> & { adquirente?: string } = {}): Item {
  const { adquirente = 'stone', ...resto } = campos
  ids += 1
  return {
    recebiveis: [
      {
        id: `r${ids}`,
        loja_id: 'loja',
        adquirente,
        trilho: 'cartao',
        vendido_em: '2026-11-01',
        liquidacao_prevista: '2026-11-05',
        liquido_centavos: 1000,
        nsu: `${ids}`,
        parcela: 1,
        parcelas: 1,
        status: 'pago',
      },
    ],
    creditos: [],
    esperado_centavos: 1000,
    caiu_centavos: 1000,
    nao_caiu_centavos: 0,
    proximo_fechamento_centavos: 0,
    severidade: null,
    motivo: null,
    pendencia_centavos: null,
    resolucao: null,
    dia: '2026-11-05',
    ...resto,
  }
}

function falta(pendencia: number, campos: Partial<Item> & { adquirente?: string } = {}): Item {
  return item({ severidade: 'falta_de_verdade', motivo: 'nao_caiu', pendencia_centavos: pendencia, ...campos })
}

function conferir(pendencia: number, campos: Partial<Item> & { adquirente?: string } = {}): Item {
  return item({ severidade: 'para_conferir', motivo: 'entrada_sem_recebivel', pendencia_centavos: pendencia, ...campos })
}

/** O fechamento de segunda, 09/11/2026: a semana vai de 03/11 a 09/11. */
function fechamento(itens: Item[]): Fechamento {
  return { rodada: { data_fechamento: '2026-11-09' }, itens } as Fechamento
}

describe('totais', () => {
  it('esperado é caiu + não caiu + próximo fechamento', () => {
    const t = totais(
      fechamento([
        item({ esperado_centavos: 1000, caiu_centavos: 1000, nao_caiu_centavos: 0, proximo_fechamento_centavos: 0 }),
        item({ esperado_centavos: 3000, caiu_centavos: 1000, nao_caiu_centavos: 1500, proximo_fechamento_centavos: 500 }),
      ]),
    )
    expect(t).toEqual({ esperado: 4000, caiu: 2000, naoCaiu: 1500, proximo: 500 })
    expect(t.caiu + t.naoCaiu + t.proximo).toBe(t.esperado)
  })

  it('o item de crédito, sem valores de grupo, não soma', () => {
    const credito = conferir(700, {
      recebiveis: [],
      esperado_centavos: null,
      caiu_centavos: null,
      nao_caiu_centavos: null,
      proximo_fechamento_centavos: null,
    })
    expect(totais(fechamento([credito]))).toEqual({ esperado: 0, caiu: 0, naoCaiu: 0, proximo: 0 })
  })
})

describe('porDia', () => {
  it('tem 8 casas: "antes" primeiro e o dia do fechamento por último', () => {
    const casas = porDia(fechamento([])).map((d) => d.casa)
    expect(casas).toEqual([
      ANTES,
      '2026-11-03',
      '2026-11-04',
      '2026-11-05',
      '2026-11-06',
      '2026-11-07',
      '2026-11-08',
      '2026-11-09',
    ])
  })

  it('item sem dia cai em "antes"', () => {
    const [antes] = porDia(fechamento([falta(500, { dia: null })]))
    expect(antes).toMatchObject({ casa: ANTES, vazio: false, faltas: 1 })
  })

  it('cada casa soma e conta os seus itens', () => {
    const dia = porDia(
      fechamento([
        item({ dia: '2026-11-05' }),
        falta(400, { dia: '2026-11-05', caiu_centavos: 600, nao_caiu_centavos: 400 }),
        conferir(200, { dia: '2026-11-05' }),
        item({ dia: '2026-11-06' }),
      ]),
    ).find((d) => d.casa === '2026-11-05')
    expect(dia).toMatchObject({
      vazio: false,
      esperado: 3000,
      caiu: 2600,
      naoCaiu: 400,
      faltas: 1,
      conferir: 1,
      certos: 1,
    })
  })

  it('dia sem item fica vazio', () => {
    const dia = porDia(fechamento([item({ dia: '2026-11-05' })])).find((d) => d.casa === '2026-11-04')
    expect(dia).toMatchObject({ vazio: true, esperado: 0, faltas: 0, conferir: 0, certos: 0 })
  })
})

describe('pendencias', () => {
  it('deixa de fora o que casou certo', () => {
    const certo = item()
    const f = falta(100)
    expect(pendencias([certo, f], SEM_FILTRO)).toEqual([f])
  })

  it('filtra por severidade', () => {
    const f = falta(100)
    const c = conferir(100)
    expect(pendencias([f, c], { ...SEM_FILTRO, severidade: 'para_conferir' })).toEqual([c])
    expect(pendencias([f, c], { ...SEM_FILTRO, severidade: 'falta_de_verdade' })).toEqual([f])
  })

  it('filtra por adquirente', () => {
    const stone = falta(100, { adquirente: 'stone' })
    const cielo = falta(100, { adquirente: 'cielo' })
    expect(pendencias([stone, cielo], { ...SEM_FILTRO, adquirente: 'cielo' })).toEqual([cielo])
  })

  it('a ordem "severidade" põe as faltas primeiro, e depois o maior valor', () => {
    const conferirGrande = conferir(9000)
    const faltaPequena = falta(100)
    const faltaGrande = falta(5000)
    expect(pendencias([conferirGrande, faltaPequena, faltaGrande], SEM_FILTRO)).toEqual([
      faltaGrande,
      faltaPequena,
      conferirGrande,
    ])
  })

  it('a ordem "valor" ignora a severidade', () => {
    const conferirGrande = conferir(9000)
    const faltaPequena = falta(100)
    expect(pendencias([faltaPequena, conferirGrande], { ...SEM_FILTRO, ordem: 'valor' })).toEqual([
      conferirGrande,
      faltaPequena,
    ])
  })

  it('a ordem "dia" põe "antes" primeiro, como na faixa', () => {
    const sexta = falta(100, { dia: '2026-11-06' })
    const terca = falta(100, { dia: '2026-11-03' })
    const antes = falta(100, { dia: null })
    expect(pendencias([sexta, terca, antes], { ...SEM_FILTRO, ordem: 'dia' })).toEqual([antes, terca, sexta])
  })
})

describe('resolução (ADR 0014)', () => {
  const resolucao = { quem: 'marina@loja.com', em: '2026-11-10T15:00:00Z', nota: 'aporte do sócio' }

  it('a pendência resolvida sai da lista e vai para Resolvidas', () => {
    const aberta = conferir(100)
    const resolvida = conferir(200, { recebiveis: [], resolucao })
    expect(pendencias([aberta, resolvida], SEM_FILTRO)).toEqual([aberta])
    expect(pendencias([aberta, resolvida], { ...SEM_FILTRO, severidade: 'para_conferir' })).toEqual([aberta])
    expect(resolvidas([aberta, resolvida, item()])).toEqual([resolvida])
  })

  it('a resolvida não conta nas abas nem na faixa', () => {
    const dia = porDia(
      fechamento([conferir(100, { dia: '2026-11-05' }), conferir(200, { dia: '2026-11-05', recebiveis: [], resolucao })]),
    ).find((d) => d.casa === '2026-11-05')
    expect(dia).toMatchObject({ conferir: 1, faltas: 0, certos: 0 })
  })
})

describe('adquirentes', () => {
  it('sem repetir, em ordem, e sem o item de crédito', () => {
    const credito = conferir(100, { recebiveis: [] })
    const f = fechamento([item({ adquirente: 'stone' }), item({ adquirente: 'cielo' }), item({ adquirente: 'stone' }), credito])
    expect(adquirentes(f)).toEqual(['cielo', 'stone'])
  })
})

describe('emPorcento', () => {
  it('arredonda para inteiro', () => {
    expect(emPorcento(1, 3)).toBe('33%')
  })

  it('total zero dá 0%', () => {
    expect(emPorcento(1, 0)).toBe('0%')
  })
})

describe('dicaDoDia', () => {
  const vazio = { casa: '2026-11-05', vazio: false, esperado: 0, caiu: 0, naoCaiu: 0, proximo: 0, faltas: 0, conferir: 0, certos: 0 }

  it('dia vazio', () => {
    expect(dicaDoDia({ ...vazio, casa: ANTES, vazio: true })).toBe('Antes desta semana: nada previsto nem caído')
  })

  it('singular e plural de "casou certo"', () => {
    expect(dicaDoDia({ ...vazio, certos: 1 })).toContain('1 casou certo')
    expect(dicaDoDia({ ...vazio, certos: 3 })).toContain('3 casaram certo')
  })

  it('"próximo fechamento" só aparece quando tem valor', () => {
    expect(dicaDoDia({ ...vazio, esperado: 1000, caiu: 1000 })).not.toContain('próximo fechamento')
    expect(dicaDoDia({ ...vazio, esperado: 1000, proximo: 1000 })).toContain('próximo fechamento')
  })
})
