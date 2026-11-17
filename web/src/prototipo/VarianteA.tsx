// PROTÓTIPO, variante A "Extrato": calma, de banco. Resumo como cartão com a barra do esperado,
// faixa de dias com medidor por dia, pendências como extrato em tabela.
import { type ReactNode, useState } from 'react'
import { hashDaSemana } from '../navegacao'
import { type Fechamento, emReais, linhaDoResumo, nomeDoDia, paraConferir, quando } from '../fechamento/textos'
import { Ajuda } from './Ajuda'
import { BarraDoEsperado, dicaDoDia } from './Graficos'
import { Filtros, Linha } from './Linhas'
import { SEM_FILTRO, adquirentes, pct, pendencias, porDia } from './numeros'

export function VarianteA({ fechamento, dia, acoes, abas = false }: { fechamento: Fechamento; dia: string | null; acoes: ReactNode; abas?: boolean }) {
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
  const dias = porDia(fechamento)
  const maior = Math.max(...dias.map((d) => d.esperado), 1)

  return (
    <div className="p-a">
      <section className="p-a-resumo" data-recomendacao={resumo.recomendacao}>
        <p className="p-a-veredito">{linhaDoResumo(resumo)}</p>
        <p className="p-a-sub">
          {paraConferir(resumo) ?? 'Nada para conferir'} · Corte em {quando(rodada.corte)} <Ajuda termo="corte" nome="Corte" />
          {resumo.limite_trava_centavos != null && (
            <>
              {' '}
              · Trava em {emReais(resumo.limite_trava_centavos)} <Ajuda termo="trava" nome="Trava" />
            </>
          )}
        </p>
        <BarraDoEsperado fechamento={fechamento} alta />
        {acoes}
      </section>

      <nav className="p-a-faixa" aria-label="Dias do fechamento">
        {dias.map((d) => {
          const escolhida = dia === d.casa
          return (
            <a
              key={d.casa}
              href={hashDaSemana(semana, escolhida ? null : d.casa)}
              aria-current={escolhida ? 'true' : undefined}
              aria-label={dicaDoDia(d)}
              data-vazio={d.vazio || undefined}
              data-corte={d.casa === semana || undefined}
            >
              <span className="p-a-dia-nome">{nomeDoDia(d.casa)}</span>
              <span className="p-a-dia-valor valor">{emReais(d.caiu)}</span>
              <span className="p-medidor" style={{ inlineSize: pct(d.esperado, maior) }}>
                <span style={{ inlineSize: pct(d.caiu, d.esperado) }} />
              </span>
              <span className="p-a-dia-marcas">
                {d.faltas > 0 && <span data-severidade="falta_de_verdade">{d.faltas} falta{d.faltas > 1 && 's'}</span>}
                {d.conferir > 0 && <span data-severidade="para_conferir">{d.conferir} conferir</span>}
              </span>
              <span className="p-dica" aria-hidden="true">
                {dicaDoDia(d)}
              </span>
            </a>
          )
        })}
      </nav>

      <section className="p-a-extrato" aria-labelledby="p-a-titulo">
        <header>
          <h2 id="p-a-titulo">
            Pendências <span className="p-contagem">{lista.length}</span>
          </h2>
          {dia !== null && (
            <p className="p-filtro-dia">
              {nomeDoDia(dia)} · <a href={hashDaSemana(semana)}>ver a semana toda</a>
            </p>
          )}
        </header>
        <Filtros filtro={filtro} mudar={setFiltro} adquirentes={adquirentes(fechamento)} contagem={contagem} abas={abas} />
        {lista.length === 0 ? (
          <p className="p-vazio">Nenhuma pendência com esses filtros.</p>
        ) : (
          <ul className="p-linhas">
            {lista.map((i) => (
              <Linha key={`${filtro.ordem}-${i.recebiveis[0]?.id ?? i.creditos[0]?.id}`} item={i} semana={semana} />
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
    </div>
  )
}
