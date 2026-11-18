import { useSyncExternalStore } from 'react'

/**
 * As telas do app, pelo hash da URL. Sem router.
 * - `#/fechamento?semana=AAAA-MM-DD&dia=AAAA-MM-DD`: a lista, filtrada por um dia da faixa (#26). `dia=antes` é "Antes desta semana".
 * - `#/fechamento/AAAA-MM-DD/item/<chave>`: o detalhe de um item. A chave é `<adquirente>:<id>` do primeiro recebível,
 *   ou o id do crédito (#26, ADR 0009).
 * - `#/limite` (#25).
 */
export type Rota =
  | { tela: 'fechamento'; semana: string | null; dia: string | null; item: null }
  | { tela: 'fechamento'; semana: string; dia: null; item: string }
  | { tela: 'limite' }

const ITEM = /^\/fechamento\/(\d{4}-\d{2}-\d{2})\/item\/(.+)$/

export function lerRota(hash: string): Rota {
  const [caminho, busca = ''] = hash.replace(/^#/, '').split('?')
  if (caminho === '/limite') return { tela: 'limite' }
  const item = ITEM.exec(caminho)
  if (item) return { tela: 'fechamento', semana: item[1], dia: null, item: decodeURIComponent(item[2]) }
  // Sem semana, a tela abre no fechamento atual. Hash desconhecido também cai no fechamento.
  const parametros = new URLSearchParams(busca)
  return { tela: 'fechamento', semana: parametros.get('semana'), dia: parametros.get('dia'), item: null }
}

export function hashDa(rota: Rota): string {
  if (rota.tela === 'limite') return '#/limite'
  if (rota.item !== null) return `#/fechamento/${rota.semana}/item/${encodeURIComponent(rota.item)}`
  const parametros = new URLSearchParams()
  if (rota.semana) parametros.set('semana', rota.semana)
  if (rota.dia) parametros.set('dia', rota.dia)
  const busca = parametros.toString()
  return busca ? `#/fechamento?${busca}` : '#/fechamento'
}

/** A lista de uma semana, com ou sem o filtro de dia. */
export function hashDaSemana(semana: string | null, dia: string | null = null): string {
  return hashDa({ tela: 'fechamento', semana, dia, item: null })
}

function assinar(avisar: () => void): () => void {
  window.addEventListener('hashchange', avisar)
  return () => window.removeEventListener('hashchange', avisar)
}

/** O hash é o estado da navegação: links comuns trocam de tela, e o voltar do navegador funciona sozinho. */
export function useRota(): Rota {
  const hash = useSyncExternalStore(assinar, () => window.location.hash)
  return lerRota(hash)
}
