import { useId, useState } from 'react'
import { hashDa, hashDaSemana } from '../navegacao'
import { type Filtro, SEM_FILTRO, adquirentes, fracao, pendencias, porDia, severidade } from './contas'
import {
  ABAS,
  type Fechamento,
  type Item,
  LEGENDA_DA_FAIXA,
  ORDENS,
  SEM_PENDENCIA_NO_FILTRO,
  casaDoItem,
  chaveDoItem,
  dicaDoDia,
  emReais,
  marcaDeConferir,
  marcaDeFaltas,
  nomeDaAdquirente,
  nomeDoDia,
  notaDoDia,
  origem,
  textoDaSeveridade,
  textoDoMotivo,
  valorDoItem,
} from './textos'

// A severidade nunca vem só pela cor: cada marca tem ícone e texto.
const ICONE = { falta_de_verdade: '!', para_conferir: '?', ok: '✓' } as const

/**
 * Os dias da semana e "Antes desta semana" (#26). Cada casa mostra quanto caiu e um medidor (#32):
 * a largura é o esperado do dia perto do maior dia, e a parte cheia é o que caiu.
 * Cada casa leva à lista filtrada por aquele dia; clicar de novo tira o filtro.
 */
export function Faixa({ fechamento, dia }: { fechamento: Fechamento; dia: string | null }) {
  const semana = fechamento.rodada.data_fechamento
  const dias = porDia(fechamento)
  const maior = Math.max(...dias.map((d) => d.esperado), 1)
  const legenda = useId()
  return (
    <div className="faixa">
      <p id={legenda} className="faixa-legenda">
        {LEGENDA_DA_FAIXA}
      </p>
      <nav className="faixa-dias" aria-label="Dias do fechamento" aria-describedby={legenda}>
        {dias.map((d) => {
          const escolhida = dia === d.casa
          return (
            <a
              key={d.casa}
              className="dia"
              href={hashDaSemana(semana, escolhida ? null : d.casa)}
              aria-current={escolhida ? 'true' : undefined}
              // A dica é visual; o leitor de tela ouve o mesmo texto pelo nome do link.
              aria-label={dicaDoDia(d)}
              data-vazio={d.vazio || undefined}
              data-corte={d.casa === semana || undefined}
            >
              <span className="dia-nome">{nomeDoDia(d.casa)}</span>
              <span className="dia-valor valor">{emReais(d.caiu)}</span>
              <span className="medidor" style={{ inlineSize: fracao(d.esperado, maior) }}>
                <span style={{ inlineSize: fracao(d.caiu, d.esperado) }} />
              </span>
              <span className="dia-marcas">
                {d.faltas > 0 && <Marca s="falta_de_verdade">{marcaDeFaltas(d.faltas)}</Marca>}
                {d.conferir > 0 && <Marca s="para_conferir">{marcaDeConferir(d.conferir)}</Marca>}
              </span>
              <span className="dica" aria-hidden="true">
                {dicaDoDia(d)}
              </span>
            </a>
          )
        })}
      </nav>
    </div>
  )
}

function Marca({ s, children }: { s: keyof typeof ICONE; children: string }) {
  return (
    <span className="selo" data-severidade={s}>
      <span aria-hidden="true">{ICONE[s]}</span>
      {children}
    </span>
  )
}

/**
 * O extrato: as pendências primeiro e "Casou certo" recolhido (#26). As abas de severidade,
 * a adquirente e a ordem filtram só as pendências (#32); o filtro do dia vem da faixa, pelo hash.
 */
export function Lista({ fechamento, dia }: { fechamento: Fechamento; dia: string | null }) {
  const semana = fechamento.rodada.data_fechamento
  const [filtro, setFiltro] = useState(SEM_FILTRO)
  const itens = fechamento.itens.filter((i) => dia === null || casaDoItem(i) === dia)
  const lista = pendencias(itens, filtro)
  const doDia = pendencias(itens, SEM_FILTRO).length
  const certos = itens.filter((i) => i.severidade == null)
  const contagem = Object.fromEntries(
    ABAS.map((a) => [a.valor, pendencias(itens, { ...filtro, severidade: a.valor }).length]),
  ) as Record<Filtro['severidade'], number>

  return (
    <section className="extrato" aria-labelledby="pendencias-titulo">
      <header>
        <h2 id="pendencias-titulo">
          Pendências <span className="contagem">{lista.length}</span>
        </h2>
        {dia !== null && (
          <p className="filtro">
            Mostrando {nomeDoDia(dia)}. <a href={hashDaSemana(semana)}>Ver a semana toda</a>
          </p>
        )}
      </header>
      {itens.length === 0 ? (
        <p className="vazio">Nada previsto nem caído neste dia.</p>
      ) : (
        <>
          {doDia > 0 && (
            <Filtros filtro={filtro} mudar={setFiltro} adquirentes={adquirentes(fechamento)} contagem={contagem} />
          )}
          {lista.length === 0 ? (
            <p className="vazio">{doDia === 0 ? 'Nenhuma pendência.' : SEM_PENDENCIA_NO_FILTRO}</p>
          ) : (
            <ul className="linhas">
              {lista.map((i) => (
                // A ordem na chave remonta as linhas ao reordenar: elas entram de novo, com a transição.
                <LinhaDoItem key={`${filtro.ordem}-${chaveDoItem(i)}`} item={i} semana={semana} />
              ))}
            </ul>
          )}
          {certos.length > 0 && (
            <details className="certos">
              <summary>Casou certo ({certos.length})</summary>
              <ul className="linhas">
                {certos.map((i) => (
                  <LinhaDoItem key={chaveDoItem(i)} item={i} semana={semana} />
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </section>
  )
}

/** Abas de severidade como rádios de verdade: as setas do teclado trocam de aba sem código. */
function Filtros({
  filtro,
  mudar,
  adquirentes,
  contagem,
}: {
  filtro: Filtro
  mudar: (f: Filtro) => void
  adquirentes: string[]
  contagem: Record<Filtro['severidade'], number>
}) {
  const nome = useId()
  return (
    <div className="filtros">
      <fieldset className="abas">
        <legend className="so-leitor">Severidade</legend>
        {ABAS.map((a) => (
          <label key={a.valor} data-severidade={a.valor}>
            <input
              type="radio"
              className="so-leitor"
              name={nome}
              checked={filtro.severidade === a.valor}
              onChange={() => mudar({ ...filtro, severidade: a.valor })}
            />
            {a.nome} <span className="abas-n">{contagem[a.valor]}</span>
          </label>
        ))}
      </fieldset>
      {/* Com uma adquirente só, o filtro não escolhe nada. */}
      {adquirentes.length > 1 && (
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
      )}
      <label>
        Ordem
        <select
          value={filtro.ordem}
          onChange={(e) => mudar({ ...filtro, ordem: e.target.value as Filtro['ordem'] })}
        >
          {ORDENS.map((o) => (
            <option key={o.valor} value={o.valor}>
              {o.nome}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}

function LinhaDoItem({ item, semana }: { item: Item; semana: string }) {
  const nota = notaDoDia(item)
  const s = severidade(item)
  return (
    <li className="linha">
      <a data-severidade={s} href={hashDa({ tela: 'fechamento', semana, dia: null, item: chaveDoItem(item) })}>
        <Marca s={s}>{item.severidade ? textoDaSeveridade(item.severidade) : 'Casou certo'}</Marca>
        <span className="linha-motivo">{item.motivo ? textoDoMotivo(item.motivo) : 'Casou certo'}</span>
        <span className="linha-origem">
          {origem(item)}
          {nota && ` · ${nota}`}
        </span>
        <span className="linha-dia">{nomeDoDia(casaDoItem(item))}</span>
        <span className="linha-valor valor">{emReais(valorDoItem(item))}</span>
      </a>
    </li>
  )
}
