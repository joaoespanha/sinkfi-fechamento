import { useSyncExternalStore } from 'react'

/** As telas do app, pelo hash da URL (#25): `#/fechamento?semana=AAAA-MM-DD` e `#/limite`. Sem router. */
export type Rota = { tela: 'fechamento'; semana: string | null } | { tela: 'limite' }

export function lerRota(hash: string): Rota {
  const [caminho, busca = ''] = hash.replace(/^#/, '').split('?')
  if (caminho === '/limite') return { tela: 'limite' }
  // Sem semana, a tela abre no fechamento atual. Hash desconhecido também cai no fechamento.
  return { tela: 'fechamento', semana: new URLSearchParams(busca).get('semana') }
}

export function hashDa(rota: Rota): string {
  if (rota.tela === 'limite') return '#/limite'
  return rota.semana ? `#/fechamento?semana=${encodeURIComponent(rota.semana)}` : '#/fechamento'
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
