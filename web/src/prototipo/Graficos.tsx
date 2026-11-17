// PROTÓTIPO (Q8a): gráficos da semana aberta, dentro do Fechamento. Sem biblioteca: divs e CSS.
import { hashDaSemana } from '../navegacao'
import { type Fechamento, emReais, nomeDoDia } from '../fechamento/textos'
import { Ajuda } from './Ajuda'
import { type Dia, pct, porDia, totais } from './numeros'

/** Barra segmentada do esperado: caiu, não caiu, próximo fechamento. Alta (A) ou fina (B). */
export function BarraDoEsperado({ fechamento, alta }: { fechamento: Fechamento; alta: boolean }) {
  const t = totais(fechamento)
  const partes = [
    { chave: 'caiu', nome: 'Caiu', valor: t.caiu, termo: 'caiu' },
    { chave: 'nao-caiu', nome: 'Não caiu', valor: t.naoCaiu, termo: 'naoCaiu' },
    { chave: 'proximo', nome: 'Próximo fechamento', valor: t.proximo, termo: 'proximo' },
  ] as const
  const descricao = partes.map((p) => `${p.nome} ${emReais(p.valor)}`).join(', ')
  return (
    <figure className="p-esperado" data-alta={alta || undefined}>
      <figcaption>
        Esperado <Ajuda termo="esperado" nome="Esperado" />
        <span className="p-esperado-total valor">{emReais(t.esperado)}</span>
      </figcaption>
      <div className="p-segmentos" role="img" aria-label={`Esperado ${emReais(t.esperado)}: ${descricao}`}>
        {partes
          .filter((p) => p.valor > 0)
          .map((p) => (
            <span
              key={p.chave}
              className="p-segmento"
              data-parte={p.chave}
              style={{ flexGrow: p.valor }}
              title={`${p.nome}: ${emReais(p.valor)} (${pct(p.valor, t.esperado).replace(/\.\d+/, '')})`}
            >
              {alta && p.valor / t.esperado > 0.12 && <span className="p-segmento-rotulo">{pct(p.valor, t.esperado).replace(/\.\d+/, '')}</span>}
            </span>
          ))}
      </div>
      <ul className="p-legenda">
        {partes.map((p) => (
          <li key={p.chave} data-parte={p.chave}>
            <span className="p-amostra" aria-hidden="true" />
            {p.nome} <Ajuda termo={p.termo} nome={p.nome} />
            <span className="valor">{emReais(p.valor)}</span>
          </li>
        ))}
      </ul>
    </figure>
  )
}

export function dicaDoDia(d: Dia): string {
  if (d.vazio) return `${nomeDoDia(d.casa)}: nada previsto nem caído`
  const marcas = [
    d.faltas && `${d.faltas} ${d.faltas === 1 ? 'falta' : 'faltas'} de verdade`,
    d.conferir && `${d.conferir} para conferir`,
    d.certos && `${d.certos} casou certo`,
  ].filter(Boolean)
  return `${nomeDoDia(d.casa)}: esperado ${emReais(d.esperado)}, caiu ${emReais(d.caiu)}, não caiu ${emReais(d.naoCaiu)}. ${marcas.join(', ')}.`
}

/** Colunas por dia (B): altura = esperado, preenchimento = caiu. Clicar filtra a lista pelo dia. */
export function ColunasPorDia({ fechamento, dia }: { fechamento: Fechamento; dia: string | null }) {
  const semana = fechamento.rodada.data_fechamento
  const dias = porDia(fechamento)
  const maior = Math.max(...dias.map((d) => d.esperado), 1)
  return (
    <figure className="p-colunas">
      <figcaption>Esperado e caiu, por dia</figcaption>
      <nav className="p-colunas-area" aria-label="Dias do fechamento">
        {dias.map((d) => {
          const escolhida = dia === d.casa
          return (
            <a
              key={d.casa}
              className="p-coluna"
              href={hashDaSemana(semana, escolhida ? null : d.casa)}
              aria-current={escolhida ? 'true' : undefined}
              aria-label={dicaDoDia(d)}
              data-corte={d.casa === semana || undefined}
              data-falta={d.faltas > 0 || undefined}
            >
              <span className="p-coluna-trilho" style={{ blockSize: pct(d.esperado, maior) }}>
                <span className="p-coluna-caiu" style={{ blockSize: pct(d.caiu, d.esperado) }} />
              </span>
              <span className="p-coluna-nome">{d.casa === 'antes' ? 'antes' : nomeDoDia(d.casa).split(',')[0]}</span>
              <span className="p-dica" aria-hidden="true">
                {dicaDoDia(d)}
              </span>
            </a>
          )
        })}
      </nav>
      <ul className="p-legenda">
        <li data-parte="esperado">
          <span className="p-amostra" aria-hidden="true" />
          Esperado
        </li>
        <li data-parte="caiu">
          <span className="p-amostra" aria-hidden="true" />
          Caiu
        </li>
      </ul>
    </figure>
  )
}
