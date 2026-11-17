// PROTÓTIPO: filtros (Q6a) e linhas de pendência, com o jeito de cada variante.
import type { ReactNode } from 'react'
import { hashDa } from '../navegacao'
import {
  type Item,
  casaDoItem,
  chaveDoItem,
  emReais,
  nomeDaAdquirente,
  nomeDoDia,
  notaDoDia,
  origem,
  textoDaSeveridade,
  textoDoMotivo,
  valorDoItem,
} from '../fechamento/textos'
import { type Filtro, severidade } from './numeros'

const ICONE = { falta_de_verdade: '!', para_conferir: '?', ok: '✓' } as const

export function Marca({ item }: { item: Item }) {
  const s = severidade(item)
  return (
    <span className="p-marca" data-severidade={s}>
      <span aria-hidden="true">{ICONE[s]}</span>
      {item.severidade ? textoDaSeveridade(item.severidade) : 'Casou certo'}
    </span>
  )
}

export function Linha({ item, semana }: { item: Item; semana: string }) {
  const nota = notaDoDia(item)
  return (
    <li className="p-linha">
      <a href={hashDa({ tela: 'fechamento', semana, dia: null, item: chaveDoItem(item) })} data-severidade={severidade(item)}>
        <Marca item={item} />
        <span className="p-linha-motivo">{item.motivo ? textoDoMotivo(item.motivo) : 'Casou certo'}</span>
        <span className="p-linha-origem">
          {origem(item)}
          {nota && ` · ${nota}`}
        </span>
        <span className="p-linha-dia">{nomeDoDia(casaDoItem(item))}</span>
        <span className="p-linha-valor valor">{emReais(valorDoItem(item))}</span>
      </a>
    </li>
  )
}

export function Filtros({
  filtro,
  mudar,
  adquirentes,
  contagem,
  abas,
}: {
  filtro: Filtro
  mudar: (f: Filtro) => void
  adquirentes: string[]
  contagem: Record<Filtro['severidade'], number>
  // B mostra a severidade em abas; A num seletor como os outros.
  abas: boolean
}) {
  const opcoes: [Filtro['severidade'], string][] = [
    ['todas', 'Todas'],
    ['falta_de_verdade', 'Faltas de verdade'],
    ['para_conferir', 'Para conferir'],
  ]
  let severidades: ReactNode
  if (abas) {
    severidades = (
      <div className="p-abas" role="radiogroup" aria-label="Severidade">
        {opcoes.map(([v, nome]) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={filtro.severidade === v}
            data-severidade={v}
            onClick={() => mudar({ ...filtro, severidade: v })}
          >
            {nome} <span className="p-abas-n">{contagem[v]}</span>
          </button>
        ))}
      </div>
    )
  } else {
    severidades = (
      <label>
        Severidade
        <select value={filtro.severidade} onChange={(e) => mudar({ ...filtro, severidade: e.target.value as Filtro['severidade'] })}>
          {opcoes.map(([v, nome]) => (
            <option key={v} value={v}>
              {nome} ({contagem[v]})
            </option>
          ))}
        </select>
      </label>
    )
  }
  return (
    <div className="p-filtros">
      {severidades}
      <label>
        Adquirente
        <select value={filtro.adquirente} onChange={(e) => mudar({ ...filtro, adquirente: e.target.value })}>
          <option value="todas">Todas</option>
          {adquirentes.map((a) => (
            <option key={a} value={a}>
              {nomeDaAdquirente(a)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Ordem
        <select value={filtro.ordem} onChange={(e) => mudar({ ...filtro, ordem: e.target.value as Filtro['ordem'] })}>
          <option value="severidade">Faltas primeiro</option>
          <option value="valor">Maior valor</option>
          <option value="dia">Dia</option>
        </select>
      </label>
    </div>
  )
}
