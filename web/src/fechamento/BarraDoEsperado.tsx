import { Ajuda } from './Ajuda'
import { totais, vendasETaxas } from './contas'
import { type Fechamento, PARTES, TERMOS, emPorcento, emReais } from './textos'

// Abaixo disso a porcentagem não cabe dentro da parte; ela continua na legenda.
const ROTULO_MINIMO = 0.12

/**
 * O esperado da semana em três partes: caiu, não caiu e próximo fechamento (#32).
 * A cor nunca vem sozinha: cada parte tem nome, valor e porcentagem na legenda, e um vão separa as partes.
 */
export function BarraDoEsperado({ fechamento }: { fechamento: Fechamento }) {
  const t = totais(fechamento)
  const v = vendasETaxas(fechamento)
  const valores = { caiu: t.caiu, naoCaiu: t.naoCaiu, proximo: t.proximo }
  const partes = PARTES.map((p) => ({ ...p, nome: TERMOS[p.termo].nome, valor: valores[p.termo] }))
  const descricao = partes.map((p) => `${p.nome} ${emReais(p.valor)}`).join(', ')

  return (
    <figure className="esperado">
      <figcaption>
        Esperado <Ajuda termo="esperado" />
        <span className="esperado-total valor">{emReais(t.esperado)}</span>
      </figcaption>
      {v && (
        <p className="taxa">
          Vendas {emReais(v.vendas)} − taxas {emReais(v.taxas)} = Esperado {emReais(t.esperado)}
        </p>
      )}
      <div className="esperado-barra" role="img" aria-label={`Esperado ${emReais(t.esperado)}: ${descricao}`}>
        {partes
          .filter((p) => p.valor > 0)
          .map((p) => (
            <span key={p.chave} className="esperado-parte" data-parte={p.chave} style={{ flexGrow: p.valor }}>
              {p.valor / t.esperado >= ROTULO_MINIMO && emPorcento(p.valor, t.esperado)}
            </span>
          ))}
      </div>
      <ul className="legenda">
        {partes.map((p) => (
          <li key={p.chave} data-parte={p.chave}>
            <span className="amostra" aria-hidden="true" />
            {p.nome} <Ajuda termo={p.termo} />
            <span className="valor">{emReais(p.valor)}</span>
            <span className="legenda-pct">{emPorcento(p.valor, t.esperado)}</span>
          </li>
        ))}
      </ul>
    </figure>
  )
}
