// As contas dos gráficos e dos filtros (#32). Tudo sobre o que a api já devolve: nenhuma rota nova.
import { ANTES, type Fechamento, type Item, casaDoItem, diasDaSemana, valorDoItem } from './textos'

export type Severidade = NonNullable<Item['severidade']> | 'ok'

export function severidade(item: Item): Severidade {
  return item.severidade ?? 'ok'
}

function soma(itens: Item[], campo: (i: Item) => number | null): number {
  return itens.reduce((s, i) => s + (campo(i) ?? 0), 0)
}

/** A resolvida (ADR 0014) não conta: nem como pendência, nem como "casou certo". */
function contar(itens: Item[], s: Severidade): number {
  return itens.filter((i) => i.resolucao == null && severidade(i) === s).length
}

/** Esperado = Caiu + Não caiu + Próximo fechamento (GLOSSARY). */
function partes(itens: Item[]) {
  return {
    esperado: soma(itens, (i) => i.esperado_centavos),
    caiu: soma(itens, (i) => i.caiu_centavos),
    naoCaiu: soma(itens, (i) => i.nao_caiu_centavos),
    proximo: soma(itens, (i) => i.proximo_fechamento_centavos),
  }
}

export const totais = (f: Fechamento) => partes(f.itens)

/**
 * De onde vem o esperado da semana: o que a maquininha mostrou menos as taxas (MDR e antecipação).
 * Nulo se algum recebível veio de rodada gravada antes do bruto: uma conta pela metade não fecharia.
 */
export function vendasETaxas(f: Fechamento): { vendas: number; taxas: number } | null {
  const recebiveis = f.itens.filter((i) => i.esperado_centavos != null).flatMap((i) => i.recebiveis)
  if (recebiveis.some((r) => r.bruto_centavos == null)) return null
  return {
    vendas: recebiveis.reduce((s, r) => s + (r.bruto_centavos ?? 0), 0),
    taxas: recebiveis.reduce((s, r) => s + (r.mdr_centavos ?? 0) + (r.antecipacao_centavos ?? 0), 0),
  }
}

/** Uma casa da faixa: "Antes desta semana" e os 7 dias. O dia de cada item vem da leitura (#26). */
export function porDia(f: Fechamento) {
  return [ANTES, ...diasDaSemana(f.rodada.data_fechamento)].map((casa) => {
    const itens = f.itens.filter((i) => casaDoItem(i) === casa)
    return {
      casa,
      vazio: itens.length === 0,
      ...partes(itens),
      faltas: contar(itens, 'falta_de_verdade'),
      conferir: contar(itens, 'para_conferir'),
      certos: contar(itens, 'ok'),
    }
  })
}

/** A adquirente do item: a do primeiro recebível. O item de crédito não tem. */
export function adquirenteDo(item: Item): string | null {
  return item.recebiveis[0]?.adquirente ?? null
}

export function adquirentes(f: Fechamento): string[] {
  return [...new Set(f.itens.map(adquirenteDo).filter((a) => a !== null))].sort()
}

export type Filtro = {
  severidade: 'todas' | NonNullable<Item['severidade']>
  adquirente: 'todas' | string
  ordem: 'severidade' | 'valor' | 'dia'
}

export const SEM_FILTRO: Filtro = { severidade: 'todas', adquirente: 'todas', ordem: 'severidade' }

const ORDENS: Record<Filtro['ordem'], (a: Item, b: Item) => number> = {
  // A ordem de antes do #32: faltas de verdade primeiro, depois o maior valor.
  severidade: (a, b) =>
    Number(a.severidade !== 'falta_de_verdade') - Number(b.severidade !== 'falta_de_verdade') ||
    valorDoItem(b) - valorDoItem(a),
  valor: (a, b) => valorDoItem(b) - valorDoItem(a),
  // Sem dia ("Antes desta semana") vem primeiro, como na faixa.
  dia: (a, b) => (a.dia ?? '').localeCompare(b.dia ?? '') || valorDoItem(b) - valorDoItem(a),
}

/** As pendências do dia escolhido (ou da semana), com os filtros da lista. */
export function pendencias(itens: Item[], filtro: Filtro): Item[] {
  return itens
    .filter((i) => i.severidade != null && i.resolucao == null)
    .filter((i) => filtro.severidade === 'todas' || i.severidade === filtro.severidade)
    .filter((i) => filtro.adquirente === 'todas' || adquirenteDo(i) === filtro.adquirente)
    .sort(ORDENS[filtro.ordem])
}

/** As pendências que a lojista marcou como resolvidas (ADR 0014): fora da lista, mas não somem. */
export function resolvidas(itens: Item[]): Item[] {
  return itens.filter((i) => i.resolucao != null)
}

/** A largura de uma parte, para o `style` de uma barra. */
export function fracao(parte: number, todo: number): string {
  return todo > 0 ? `${(parte / todo) * 100}%` : '0%'
}
