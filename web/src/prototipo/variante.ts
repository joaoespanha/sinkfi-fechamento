// PROTÓTIPO (Q5c): descartável. Duas direções de identidade visual para o Fechamento, ao lado da tela atual.
// A variante vem de `?variant=` (antes do #, para não brigar com as rotas por hash). Sem o parâmetro, a tela atual.
import { useSyncExternalStore } from 'react'

export const VARIANTES = ['atual', 'A', 'B', 'C'] as const
export type Variante = (typeof VARIANTES)[number]
export const NOMES: Record<Variante, string> = { atual: 'Atual', A: 'Extrato', B: 'Painel', C: 'Gráficos da A, paleta da B' }

const EVENTO = 'prototipo:variante'

function ler(): Variante {
  const v = new URLSearchParams(location.search).get('variant')
  return (VARIANTES as readonly string[]).includes(v ?? '') ? (v as Variante) : 'atual'
}

function aplicar(v: Variante) {
  if (v === 'atual') delete document.documentElement.dataset.variante
  else document.documentElement.dataset.variante = v
}

export function trocar(v: Variante) {
  const url = new URL(location.href)
  if (v === 'atual') url.searchParams.delete('variant')
  else url.searchParams.set('variant', v)
  history.replaceState(null, '', url)
  aplicar(v)
  window.dispatchEvent(new Event(EVENTO))
}

export function useVariante(): Variante {
  return useSyncExternalStore(
    (avisar) => {
      window.addEventListener(EVENTO, avisar)
      return () => window.removeEventListener(EVENTO, avisar)
    },
    ler,
  )
}

// Na carga: marca o <html> e traz as fontes das duas direções.
aplicar(ler())
const fontes = document.createElement('link')
fontes.rel = 'stylesheet'
fontes.href =
  'https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400..700&family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap'
document.head.append(fontes)
