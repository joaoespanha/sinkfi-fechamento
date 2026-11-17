import { hashDa, hashDaSemana } from '../navegacao'
import {
  ANTES,
  type Fechamento,
  type Item,
  casaDoItem,
  chaveDoItem,
  diasDaSemana,
  emReais,
  nomeDoDia,
  notaDoDia,
  origem,
  textoDoMotivo,
  valorDoItem,
} from './textos'

type Severidade = NonNullable<Item['severidade']> | 'ok'

function severidade(item: Item): Severidade {
  return item.severidade ?? 'ok'
}

function contar(itens: Item[], s: Severidade): number {
  return itens.filter((i) => severidade(i) === s).length
}

/**
 * Os dias da semana e "Antes desta semana" (#26). Cada casa leva à lista filtrada por aquele dia;
 * clicar de novo tira o filtro. O dia de cada item vem da leitura, não é calculado aqui.
 */
export function Faixa({ fechamento, dia }: { fechamento: Fechamento; dia: string | null }) {
  const semana = fechamento.rodada.data_fechamento
  const casas = [ANTES, ...diasDaSemana(semana)]
  return (
    <nav className="faixa" aria-label="Dias do fechamento">
      {casas.map((casa) => {
        const itens = fechamento.itens.filter((i) => casaDoItem(i) === casa)
        const esperado = itens.reduce((s, i) => s + (i.esperado_centavos ?? 0), 0)
        const caiu = itens.reduce((s, i) => s + (i.caiu_centavos ?? 0), 0)
        const faltas = contar(itens, 'falta_de_verdade')
        const conferir = contar(itens, 'para_conferir')
        const certos = contar(itens, 'ok')
        const escolhida = dia === casa
        return (
          <a
            key={casa}
            className="dia"
            href={hashDaSemana(semana, escolhida ? null : casa)}
            aria-current={escolhida ? 'true' : undefined}
            data-vazio={itens.length === 0 || undefined}
            data-corte={casa === semana || undefined}
          >
            <span className="dia-nome">{nomeDoDia(casa)}</span>
            {casa === semana && <span className="dia-corte">corte</span>}
            <span className="dia-linha">esperado {emReais(esperado)}</span>
            <span className="dia-linha">caiu {emReais(caiu)}</span>
            <span className="dia-marcas">
              {faltas > 0 && <span className="chip" data-severidade="falta_de_verdade">{faltas === 1 ? '1 falta' : `${faltas} faltas`}</span>}
              {conferir > 0 && <span className="chip" data-severidade="para_conferir">{conferir} conferir</span>}
              {certos > 0 && <span className="chip" data-severidade="ok">{certos} ok</span>}
            </span>
          </a>
        )
      })}
    </nav>
  )
}

/** As pendências primeiro (faltas de verdade, depois o maior valor) e "Casou certo" recolhido (#26). */
export function Lista({ fechamento, dia }: { fechamento: Fechamento; dia: string | null }) {
  const semana = fechamento.rodada.data_fechamento
  const itens = fechamento.itens.filter((i) => dia === null || casaDoItem(i) === dia)
  const pendencias = itens
    .filter((i) => i.severidade != null)
    .sort(
      (a, b) =>
        Number(a.severidade !== 'falta_de_verdade') - Number(b.severidade !== 'falta_de_verdade') ||
        valorDoItem(b) - valorDoItem(a),
    )
  const certos = itens.filter((i) => i.severidade == null)

  return (
    <>
      {dia !== null && (
        <p className="filtro">
          Mostrando {nomeDoDia(dia)}. <a href={hashDaSemana(semana)}>Ver a semana toda</a>
        </p>
      )}
      {itens.length === 0 ? (
        <p>Nada previsto nem caído neste dia.</p>
      ) : (
        <>
          <section className="lista" aria-labelledby="pendencias-titulo">
            <h2 id="pendencias-titulo">Pendências ({pendencias.length})</h2>
            {pendencias.length === 0 ? (
              <p>Nenhuma pendência.</p>
            ) : (
              <ul>
                {pendencias.map((i) => (
                  <LinhaDoItem key={chaveDoItem(i)} item={i} semana={semana} />
                ))}
              </ul>
            )}
          </section>
          {certos.length > 0 && (
            <details className="certos">
              <summary>Casou certo ({certos.length})</summary>
              <ul className="lista">
                {certos.map((i) => (
                  <LinhaDoItem key={chaveDoItem(i)} item={i} semana={semana} />
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </>
  )
}

function LinhaDoItem({ item, semana }: { item: Item; semana: string }) {
  const nota = notaDoDia(item)
  return (
    <li>
      <a
        className="item"
        data-severidade={severidade(item)}
        href={hashDa({ tela: 'fechamento', semana, dia: null, item: chaveDoItem(item) })}
      >
        <span className="item-motivo">{item.motivo ? textoDoMotivo(item.motivo) : 'Casou certo'}</span>
        <span className="item-valor valor">{emReais(valorDoItem(item))}</span>
        <span className="item-origem">
          {origem(item)}
          {nota && ` · ${nota}`}
        </span>
      </a>
    </li>
  )
}
