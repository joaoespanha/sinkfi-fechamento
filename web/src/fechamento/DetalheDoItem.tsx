import { hashDaSemana } from '../navegacao'
import {
  type Fechamento,
  type Item,
  acharItem,
  diaDaSemana,
  emReais,
  explicacaoDoMotivo,
  linhaDoCredito,
  linhaDoRecebivel,
  notaDoDia,
  oQueFazer,
  quando,
  textoDaChave,
  textoDaSeveridade,
  textoDoMotivo,
  valorDoItem,
} from './textos'

type Passo = { nome: string; quando: string; estado: 'feito' | 'falhou' | null }

/** Vendida, prevista, caiu e corte. O item de crédito só tem o "caiu" e o corte. */
function linhaDoTempo(item: Item, corte: string): Passo[] {
  const passos: Passo[] = []
  const r = item.recebiveis[0]
  if (r) {
    const prevista = item.recebiveis.map((x) => x.liquidacao_prevista).sort().at(-1) ?? r.liquidacao_prevista
    passos.push({ nome: 'Vendida', quando: diaDaSemana(r.vendido_em), estado: 'feito' })
    passos.push({ nome: 'Prevista', quando: diaDaSemana(prevista), estado: 'feito' })
  }
  const c = item.creditos[0]
  passos.push(
    c
      ? { nome: 'Caiu', quando: quando(c.lancado_em), estado: item.severidade === 'falta_de_verdade' ? 'falhou' : 'feito' }
      : { nome: 'Caiu', quando: 'não caiu', estado: 'falhou' },
  )
  passos.push({ nome: 'Corte', quando: quando(corte), estado: null })
  return passos
}

/** A página de um item (#26): qualquer item tem uma, inclusive o que casou certo. */
export function DetalheDoItem({ fechamento, chave }: { fechamento: Fechamento; chave: string }) {
  const semana = fechamento.rodada.data_fechamento
  const voltar = (
    <a className="voltar" href={hashDaSemana(semana)}>
      ‹ Fechamento de {diaDaSemana(semana)}
    </a>
  )
  const item = acharItem(fechamento.itens, chave)
  if (!item) {
    return (
      <>
        {voltar}
        <p role="alert">Este item não está neste fechamento.</p>
      </>
    )
  }

  const titulo = item.motivo ? textoDoMotivo(item.motivo) : 'Casou certo'
  const nota = notaDoDia(item)
  const grupo = item.esperado_centavos !== null

  return (
    <article className="detalhe" data-severidade={item.severidade ?? 'ok'}>
      {voltar}
      <header className="titulo">
        <h1>
          {titulo} · {emReais(valorDoItem(item))}
        </h1>
        {item.severidade && <span className="detalhe-severidade">{textoDaSeveridade(item.severidade)}</span>}
      </header>

      <p>{item.motivo ? explicacaoDoMotivo(item.motivo) : textoDaChave(item)}</p>
      {nota && <p className="ajuda">Esta venda {nota}.</p>}

      <ol className="tempo" aria-label="Linha do tempo">
        {linhaDoTempo(item, fechamento.rodada.corte).map((p) => (
          <li key={p.nome} data-estado={p.estado ?? undefined}>
            <span>{p.nome}</span>
            {p.quando}
          </li>
        ))}
      </ol>

      {item.motivo && (
        <section className="fazer" aria-labelledby="fazer-titulo">
          <h2 id="fazer-titulo">O que fazer</h2>
          <p>{oQueFazer(item.motivo, item)}</p>
        </section>
      )}

      {grupo && (
        <dl className="valores">
          <dt>Esperado</dt>
          <dd>{emReais(item.esperado_centavos ?? 0)}</dd>
          <dt>Caiu</dt>
          <dd>{emReais(item.caiu_centavos ?? 0)}</dd>
          <dt>Não caiu</dt>
          <dd>{emReais(item.nao_caiu_centavos ?? 0)}</dd>
          <dt>Próximo fechamento</dt>
          <dd>{emReais(item.proximo_fechamento_centavos ?? 0)}</dd>
        </dl>
      )}

      {item.recebiveis.length > 0 && (
        <section className="bloco">
          <h2>Recebíveis</h2>
          <ul>
            {item.recebiveis.map((r) => (
              <li key={r.id}>
                {linhaDoRecebivel(r)} · <span className="valor">{emReais(r.liquido_centavos)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
      <section className="bloco">
        <h2>Créditos</h2>
        {item.creditos.length > 0 ? (
          <ul>
            {item.creditos.map((c) => (
              <li key={c.id}>
                {linhaDoCredito(c)} · <span className="valor">{emReais(c.valor_centavos)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p>Nenhum crédito casou com este item.</p>
        )}
      </section>
    </article>
  )
}
