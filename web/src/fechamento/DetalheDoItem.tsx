import { useRef, useState } from 'react'
import { type Acoes, enviar } from '../enviar'
import { hashDaSemana } from '../navegacao'
import {
  type Fechamento,
  type Item,
  NOTA_MAXIMA,
  acharItem,
  chaveDoRecebivel,
  diaDaSemana,
  emReais,
  explicacaoDoMotivo,
  fraseDaResolucao,
  linhaDoCredito,
  linhaDoRecebivel,
  notaDoDia,
  oQueFazer,
  podeResolver,
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

/**
 * A página de um item (#26): qualquer item tem uma, inclusive o que casou certo.
 * Só a lojista resolve e desfaz (ADR 0014); o suporte vê a resolução, sem os botões.
 */
export function DetalheDoItem({
  fechamento,
  chave,
  clienteId,
  lojista,
  acoes,
}: {
  fechamento: Fechamento
  chave: string
  clienteId: string
  lojista: boolean
  acoes: Acoes
}) {
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

      {(item.resolucao || (lojista && podeResolver(item))) && (
        <Resolucao item={item} rodadaId={fechamento.rodada.id} clienteId={clienteId} lojista={lojista} acoes={acoes} />
      )}

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
              <li key={chaveDoRecebivel(r)}>
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

/**
 * A resolução de uma pendência para conferir (ADR 0014). Resolvida: quem, quando, a nota (texto puro) e o
 * Desfazer. Aberta: o botão e o `<dialog>` com a nota, no padrão da conferência (ADR 0012).
 */
function Resolucao({
  item,
  rodadaId,
  clienteId,
  lojista,
  acoes,
}: {
  item: Item
  rodadaId: number
  clienteId: string
  lojista: boolean
  acoes: Acoes
}) {
  const [enviando, setEnviando] = useState(false)
  const [falhou, setFalhou] = useState(false)
  const dialogo = useRef<HTMLDialogElement>(null)
  const campo = useRef<HTMLTextAreaElement>(null)
  const cliente = encodeURIComponent(clienteId)
  // `podeResolver` garante um crédito só: a resolução é presa a esse lançamento.
  const lancamentoId = item.creditos[0]?.id ?? ''

  async function registrar(pedido: () => Promise<Response>) {
    setFalhou(false)
    setEnviando(true)
    try {
      const resposta = await pedido()
      if (resposta.status === 401) return acoes.aoPerderSessao()
      if (!resposta.ok) return setFalhou(true)
      acoes.recarregar()
    } catch (erro: unknown) {
      console.error(erro)
      setFalhou(true)
    } finally {
      setEnviando(false)
    }
  }

  function abrir() {
    setFalhou(false)
    dialogo.current?.showModal()
    // O autoFocus do React só age na montagem, com o diálogo fechado: o foco vai para a nota aqui.
    campo.current?.focus()
  }

  /** Só espaço não é nota: o servidor recusaria, então o navegador já avisa. */
  function conferirNota() {
    const c = campo.current
    c?.setCustomValidity(c.value.trim() === '' && c.value !== '' ? 'Escreva o que é esta entrada.' : '')
  }

  function aoFechar() {
    const d = dialogo.current
    const c = campo.current
    if (!d || !c) return
    // Esc não define valor e o navegador pode manter o anterior: zera para a próxima vez.
    const escolha = d.returnValue
    d.returnValue = ''
    const nota = c.value.trim()
    if (escolha !== 'resolver' || nota === '') return
    c.value = ''
    void registrar(() =>
      enviar(`/clientes/${cliente}/resolucoes`, 'POST', { rodada_id: rodadaId, lancamento_id: lancamentoId, nota }),
    )
  }

  if (item.resolucao) {
    return (
      <section className="resolucao" aria-labelledby="resolucao-titulo">
        <h2 id="resolucao-titulo">{fraseDaResolucao(item.resolucao)}</h2>
        <p className="resolucao-nota">{item.resolucao.nota}</p>
        {lojista && (
          <>
            <button
              type="button"
              disabled={enviando}
              onClick={() =>
                void registrar(() =>
                  fetch(`/api/clientes/${cliente}/resolucoes/${encodeURIComponent(lancamentoId)}`, {
                    method: 'DELETE',
                  }),
                )
              }
            >
              Desfazer
            </button>
            <p role="status">{falhou ? 'Não foi possível desfazer. Tente de novo.' : ''}</p>
          </>
        )}
      </section>
    )
  }

  return (
    <section className="resolucao" aria-labelledby="resolucao-titulo">
      <h2 id="resolucao-titulo">Já sabe o que é?</h2>
      <p>Marque como resolvida: sai da lista e das contagens, e fica com a sua nota em Resolvidas.</p>
      <button type="button" onClick={abrir} disabled={enviando}>
        Marcar como resolvida
      </button>
      <p role="status">{falhou ? 'Não foi possível registrar. Tente de novo.' : ''}</p>
      <dialog ref={dialogo} aria-labelledby="resolver-titulo" onClose={aoFechar}>
        <h2 id="resolver-titulo">Marcar como resolvida?</h2>
        <form method="dialog">
          <label htmlFor="resolver-nota">O que é esta entrada</label>
          <textarea
            ref={campo}
            id="resolver-nota"
            name="nota"
            required
            maxLength={NOTA_MAXIMA}
            rows={3}
            aria-describedby="resolver-ajuda"
            onInput={conferirNota}
          />
          <p id="resolver-ajuda" className="ajuda">
            Por exemplo, &ldquo;aporte do sócio&rdquo;. Até {NOTA_MAXIMA} caracteres. Quem atende o suporte vê esta nota.
          </p>
          <div className="resolucao-botoes">
            <button value="cancelar" formNoValidate>
              Cancelar
            </button>
            <button value="resolver" className="primario">
              Marcar como resolvida
            </button>
          </div>
        </form>
      </dialog>
    </section>
  )
}
