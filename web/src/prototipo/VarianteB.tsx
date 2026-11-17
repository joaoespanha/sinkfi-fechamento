// PROTÓTIPO, variante B "Painel": decisão à esquerda, números à direita. O veredito ocupa uma faixa
// colorida; a lista vem em abas por severidade; os dias viram um gráfico de colunas na coluna lateral.
import { type ReactNode, useState } from 'react'
import { hashDaSemana } from '../navegacao'
import { type Fechamento, emReais, linhaDoResumo, nomeDoDia, paraConferir, quando } from '../fechamento/textos'
import { Ajuda } from './Ajuda'
import { BarraDoEsperado, ColunasPorDia } from './Graficos'
import { Filtros, Linha } from './Linhas'
import { SEM_FILTRO, adquirentes, pendencias } from './numeros'

const ICONE = { pode_fechar: '✓', faltam: '!', nao_feche: '✕' } as const

export function VarianteB({ fechamento, dia, acoes }: { fechamento: Fechamento; dia: string | null; acoes: ReactNode }) {
  const { resumo, rodada } = fechamento
  const semana = rodada.data_fechamento
  const [filtro, setFiltro] = useState(SEM_FILTRO)
  const lista = pendencias(fechamento, dia, filtro)
  const contagem = {
    todas: pendencias(fechamento, dia, { ...filtro, severidade: 'todas' }).length,
    falta_de_verdade: pendencias(fechamento, dia, { ...filtro, severidade: 'falta_de_verdade' }).length,
    para_conferir: pendencias(fechamento, dia, { ...filtro, severidade: 'para_conferir' }).length,
  }
  const certos = fechamento.itens.filter((i) => i.severidade == null && (dia === null || i.dia === dia))

  return (
    <div className="p-b">
      <section className="p-b-veredito" data-recomendacao={resumo.recomendacao}>
        <span className="p-b-icone" aria-hidden="true">
          {ICONE[resumo.recomendacao as keyof typeof ICONE] ?? '!'}
        </span>
        <div>
          <p className="p-b-linha">{linhaDoResumo(resumo)}</p>
          <p className="p-b-sub">
            {resumo.itens_falta_de_verdade} {resumo.itens_falta_de_verdade === 1 ? 'falta' : 'faltas'} de verdade{' '}
            <Ajuda termo="falta" nome="Falta de verdade" /> · {paraConferir(resumo) ?? 'nada para conferir'}{' '}
            <Ajuda termo="conferir" nome="Para conferir" />
          </p>
        </div>
      </section>
      {acoes}

      <div className="p-b-grade">
        <section className="p-b-lista" aria-labelledby="p-b-titulo">
          <h2 id="p-b-titulo">O que olhar</h2>
          {dia !== null && (
            <p className="p-filtro-dia">
              Só {nomeDoDia(dia)} · <a href={hashDaSemana(semana)}>ver a semana toda</a>
            </p>
          )}
          <Filtros filtro={filtro} mudar={setFiltro} adquirentes={adquirentes(fechamento)} contagem={contagem} abas />
          {lista.length === 0 ? (
            <p className="p-vazio">Nada aqui com esses filtros.</p>
          ) : (
            <ul className="p-linhas">
              {lista.map((i) => (
                <Linha key={`${filtro.ordem}-${filtro.severidade}-${i.recebiveis[0]?.id ?? i.creditos[0]?.id}`} item={i} semana={semana} />
              ))}
            </ul>
          )}
          {certos.length > 0 && (
            <details className="p-certos">
              <summary>Casou certo ({certos.length})</summary>
              <ul className="p-linhas">
                {certos.map((i) => (
                  <Linha key={i.recebiveis[0]?.id ?? i.creditos[0]?.id} item={i} semana={semana} />
                ))}
              </ul>
            </details>
          )}
        </section>

        <aside className="p-b-numeros" aria-label="A semana em números">
          <h2>A semana em números</h2>
          <BarraDoEsperado fechamento={fechamento} alta={false} />
          <ColunasPorDia fechamento={fechamento} dia={dia} />
          <p className="p-b-corte">
            Corte em {quando(rodada.corte)} <Ajuda termo="corte" nome="Corte" />
          </p>
          {resumo.limite_trava_centavos != null && (
            <p className="p-b-corte">
              Trava em {emReais(resumo.limite_trava_centavos)} <Ajuda termo="trava" nome="Trava" />
            </p>
          )}
        </aside>
      </div>
    </div>
  )
}
