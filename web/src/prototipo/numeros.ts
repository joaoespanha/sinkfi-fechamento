// PROTÓTIPO: as contas dos gráficos, todas sobre o que a api já devolve (sem rota nova).
import { ANTES, type Fechamento, type Item, casaDoItem, diasDaSemana, valorDoItem } from '../fechamento/textos'

export type Severidade = NonNullable<Item['severidade']> | 'ok'
export const severidade = (i: Item): Severidade => i.severidade ?? 'ok'

const soma = (itens: Item[], f: (i: Item) => number | null) => itens.reduce((s, i) => s + (f(i) ?? 0), 0)

export type Dia = {
  casa: string
  esperado: number
  caiu: number
  naoCaiu: number
  faltas: number
  conferir: number
  certos: number
  vazio: boolean
}

export function porDia(f: Fechamento): Dia[] {
  return [ANTES, ...diasDaSemana(f.rodada.data_fechamento)].map((casa) => {
    const itens = f.itens.filter((i) => casaDoItem(i) === casa)
    return {
      casa,
      esperado: soma(itens, (i) => i.esperado_centavos),
      caiu: soma(itens, (i) => i.caiu_centavos),
      naoCaiu: soma(itens, (i) => i.nao_caiu_centavos),
      faltas: itens.filter((i) => severidade(i) === 'falta_de_verdade').length,
      conferir: itens.filter((i) => severidade(i) === 'para_conferir').length,
      certos: itens.filter((i) => severidade(i) === 'ok').length,
      vazio: itens.length === 0,
    }
  })
}

/** Esperado = Caiu + Não caiu + Próximo fechamento (GLOSSARY). */
export function totais(f: Fechamento) {
  return {
    esperado: soma(f.itens, (i) => i.esperado_centavos),
    caiu: soma(f.itens, (i) => i.caiu_centavos),
    naoCaiu: soma(f.itens, (i) => i.nao_caiu_centavos),
    proximo: soma(f.itens, (i) => i.proximo_fechamento_centavos),
    certos: f.itens.filter((i) => i.severidade == null).length,
  }
}

export const adquirenteDo = (i: Item): string | null => i.recebiveis[0]?.adquirente ?? null

export function adquirentes(f: Fechamento): string[] {
  return [...new Set(f.itens.map(adquirenteDo).filter((a): a is string => a !== null))].sort()
}

export type Filtro = {
  severidade: 'todas' | 'falta_de_verdade' | 'para_conferir'
  adquirente: string
  ordem: 'severidade' | 'valor' | 'dia'
}
export const SEM_FILTRO: Filtro = { severidade: 'todas', adquirente: 'todas', ordem: 'severidade' }

export function pendencias(f: Fechamento, dia: string | null, filtro: Filtro): Item[] {
  const ordens = {
    severidade: (a: Item, b: Item) =>
      Number(a.severidade !== 'falta_de_verdade') - Number(b.severidade !== 'falta_de_verdade') ||
      valorDoItem(b) - valorDoItem(a),
    valor: (a: Item, b: Item) => valorDoItem(b) - valorDoItem(a),
    dia: (a: Item, b: Item) => casaDoItem(a).localeCompare(casaDoItem(b)),
  }
  return f.itens
    .filter((i) => i.severidade != null)
    .filter((i) => dia === null || casaDoItem(i) === dia)
    .filter((i) => filtro.severidade === 'todas' || i.severidade === filtro.severidade)
    .filter((i) => filtro.adquirente === 'todas' || adquirenteDo(i) === filtro.adquirente)
    .sort(ordens[filtro.ordem])
}

export const pct = (parte: number, todo: number) => (todo > 0 ? `${(parte / todo) * 100}%` : '0%')
