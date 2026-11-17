// PROTÓTIPO: a barra flutuante que troca de variante. Só no `npm run dev`.
import { useEffect } from 'react'
import { NOMES, VARIANTES, trocar, useVariante } from './variante'

export function Alternador() {
  const atual = useVariante()
  const i = VARIANTES.indexOf(atual)
  const ir = (passo: number) => trocar(VARIANTES[(i + passo + VARIANTES.length) % VARIANTES.length])

  useEffect(() => {
    function tecla(e: KeyboardEvent) {
      const alvo = e.target as HTMLElement
      if (alvo.closest('input, textarea, select, [contenteditable]')) return
      if (e.key === 'ArrowLeft') ir(-1)
      if (e.key === 'ArrowRight') ir(1)
    }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  })

  if (!import.meta.env.DEV) return null
  return (
    <div className="p-alternador" role="toolbar" aria-label="Protótipo: variante">
      <button type="button" onClick={() => ir(-1)} aria-label="Variante anterior">
        ←
      </button>
      <span>
        {atual === 'atual' ? 'Atual' : `${atual} (${NOMES[atual]})`} · {i + 1}/{VARIANTES.length}
      </span>
      <button type="button" onClick={() => ir(1)} aria-label="Próxima variante">
        →
      </button>
    </div>
  )
}
