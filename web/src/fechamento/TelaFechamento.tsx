import { useEffect, useRef, useState } from 'react'
import { type Acoes, enviar } from '../enviar'
import { hashDa, hashDaSemana } from '../navegacao'
import { Ajuda } from './Ajuda'
import { BarraDoEsperado } from './BarraDoEsperado'
import { DetalheDoItem } from './DetalheDoItem'
import { Faixa, Lista } from './Lista'
import {
  avisoDaConfirmacao,
  type Fechamento,
  fraseDoConferido,
  podeConferir,
  type Semana,
  diaDaSemana,
  emReais,
  fraseDaFaixa,
  fraseDaConferencia,
  linhaDaAtualizacao,
  linhaDoResumo,
  PEDIDO_ENVIADO,
  paraConferir,
  quando,
  textoDoAviso,
} from './textos'

type Estado =
  | { tipo: 'carregando' }
  | { tipo: 'calculando' }
  | { tipo: 'demorou' }
  | { tipo: 'erro' }
  | { tipo: 'pronto'; fechamento: Fechamento }

// A rodada pedida chega pelo worker (ADR 0004): consulta de novo a cada 2 s, por até 30 s.
const INTERVALO_MS = 2_000
const PRAZO_MS = 30_000

function esperar(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const relogio = setTimeout(resolve, ms)
    signal.addEventListener(
      'abort',
      () => {
        clearTimeout(relogio)
        reject(signal.reason)
      },
      { once: true },
    )
  })
}

/** Consulta até a rodada existir. null quando o prazo acaba antes. */
async function esperarRodada(url: string, signal: AbortSignal): Promise<Response | null> {
  const prazo = AbortSignal.any([signal, AbortSignal.timeout(PRAZO_MS)])
  try {
    for (;;) {
      await esperar(INTERVALO_MS, prazo)
      const resposta = await fetch(url, { signal: prazo })
      if (resposta.status !== 404) return resposta
    }
  } catch (erro: unknown) {
    // O prazo aborta com TimeoutError; sair da tela aborta com AbortError, que sobe.
    if (erro instanceof DOMException && erro.name === 'TimeoutError') return null
    throw erro
  }
}

export function TelaFechamento({
  clienteId,
  suporte,
  escolhida,
  dia,
  item,
  aoPerderSessao,
}: {
  clienteId: string
  // null para a lojista. O suporte vê a mesma tela, com a faixa dele por cima.
  suporte: { nomeDoCliente: string } | null
  // A semana do hash (#25); null abre o fechamento atual.
  escolhida: string | null
  // O filtro da faixa de dias e o item aberto (#26), também do hash.
  dia: string | null
  item: string | null
  // 401: o token venceu (8 horas) ou o usuário foi desativado. A tela volta ao login.
  aoPerderSessao: () => void
}) {
  const [semanas, setSemanas] = useState<Semana[] | null>(null)
  // O estado vale para a semana em que foi carregado: trocar de semana mostra "carregando" sem resto da anterior.
  const [carga, setCarga] = useState<{ semana: string; estado: Estado } | null>(null)
  // Muda depois de cada escrita para buscar tudo de novo, sem voltar a "carregando".
  const [versao, setVersao] = useState(0)
  // Muda quando a rodada pedida chega: a lista passa a dizer que a semana tem rodada.
  const [versaoDaLista, setVersaoDaLista] = useState(0)
  const [erroDaLista, setErroDaLista] = useState(false)

  useEffect(() => {
    const controle = new AbortController()
    fetch(`/api/clientes/${encodeURIComponent(clienteId)}/semanas`, { signal: controle.signal })
      .then(async (resposta) => {
        if (resposta.status === 401) return aoPerderSessao()
        if (!resposta.ok) return setErroDaLista(true)
        setSemanas((await resposta.json()) as Semana[])
      })
      .catch((erro: unknown) => {
        if (!controle.signal.aborted) {
          console.error(erro)
          setErroDaLista(true)
        }
      })
    return () => controle.abort()
  }, [clienteId, aoPerderSessao, versao, versaoDaLista])

  // Sem semana no endereço, a tela abre no fechamento atual.
  const semana = escolhida ?? semanas?.find((s) => s.atual)?.semana ?? null
  // Recarregar a lista não busca o fechamento de novo: só importa se ela já chegou.
  const listaChegou = semanas !== null

  useEffect(() => {
    if (!listaChegou || semana === null) return
    const controle = new AbortController()
    const cliente = encodeURIComponent(clienteId)
    const url = `/api/clientes/${cliente}/fechamento?semana=${encodeURIComponent(semana)}`
    const setEstado = (estado: Estado) => setCarga({ semana, estado })

    async function carregar(): Promise<void> {
      let resposta = await fetch(url, { signal: controle.signal })
      if (resposta.status === 404) {
        // Semana sem rodada: pede o cálculo pela fila e espera a rodada chegar.
        const pedido = await enviar(`/clientes/${cliente}/fechamentos`, 'POST', { semana })
        if (pedido.status === 401) return aoPerderSessao()
        if (!pedido.ok) return setEstado({ tipo: 'erro' })
        setEstado({ tipo: 'calculando' })
        const chegou = await esperarRodada(url, controle.signal)
        if (chegou === null) return setEstado({ tipo: 'demorou' })
        resposta = chegou
        setVersaoDaLista((v) => v + 1)
      }
      if (resposta.status === 401) return aoPerderSessao()
      if (!resposta.ok) return setEstado({ tipo: 'erro' })
      setEstado({ tipo: 'pronto', fechamento: (await resposta.json()) as Fechamento })
    }

    carregar().catch((erro: unknown) => {
      if (!controle.signal.aborted) {
        console.error(erro)
        setEstado({ tipo: 'erro' })
      }
    })
    return () => controle.abort()
  }, [clienteId, aoPerderSessao, semana, listaChegou, versao])

  const estado: Estado = erroDaLista
    ? { tipo: 'erro' }
    : carga && carga.semana === semana
      ? carga.estado
      : { tipo: 'carregando' }
  const acoes: Acoes = { aoPerderSessao, recarregar: () => setVersao((v) => v + 1) }

  return (
    <>
      {suporte && (
        <FaixaDoSuporte
          // Trocar de semana limpa o "Pedido enviado" da semana anterior.
          key={semana}
          nomeDoCliente={suporte.nomeDoCliente}
          clienteId={clienteId}
          semana={semana}
          fechamento={estado.tipo === 'pronto' ? estado.fechamento : null}
          acoes={acoes}
        />
      )}
      {semanas && <Avisos semanas={semanas} />}
      {item === null && (
        <header className="titulo">
          <h1>{semana ? `Fechamento de ${diaDaSemana(semana)}` : 'Fechamento'}</h1>
          {semanas && semana && <Setas semanas={semanas} semana={semana} />}
        </header>
      )}
      {(() => {
        // Lista vazia: o cliente ainda não tem liquidação prevista, então não há fechamento.
        if (listaChegou && semana === null) return <p>Ainda não há fechamento calculado.</p>
        // Semana do hash fora da lista (link velho ou digitado): não pede cálculo, a api recusaria.
        if (semanas && semana && !semanas.some((s) => s.semana === semana)) {
          return (
            <p role="alert">
              Este fechamento não está na lista. <a href={hashDaSemana(null)}>Ver o atual</a>
            </p>
          )
        }
        switch (estado.tipo) {
          case 'carregando':
            return <p aria-busy="true">Carregando o fechamento…</p>
          case 'calculando':
            return <p aria-busy="true">Calculando o fechamento…</p>
          case 'demorou':
            return (
              <div role="alert">
                <p>O cálculo não terminou; tente de novo.</p>
                <button type="button" onClick={acoes.recarregar}>
                  Tentar de novo
                </button>
              </div>
            )
          case 'erro':
            return <p role="alert">Não foi possível carregar o fechamento. Tente de novo em instantes.</p>
          case 'pronto':
            if (item !== null) return <DetalheDoItem fechamento={estado.fechamento} chave={item} />
            return (
              <Detalhe
                dia={dia}
                fechamento={estado.fechamento}
                clienteId={clienteId}
                // Só a lojista muda o limite e marca o fechamento como conferido (ADR 0005); o suporte só olha.
                lojista={suporte === null}
                acoes={acoes}
              />
            )
        }
      })()}
    </>
  )
}

/** Fechamentos anteriores ao atual com pendência e sem conferência. Lê as conferências; não é estado (ADR 0003). */
function Avisos({ semanas }: { semanas: Semana[] }) {
  const comAviso = semanas.filter((s) => s.aviso)
  if (comAviso.length === 0) return null
  return (
    <section className="avisos" aria-label="Fechamentos sem conferência">
      {comAviso.map((s) => (
        <p key={s.semana}>
          {textoDoAviso(s)}{' '}
          <a href={hashDaSemana(s.semana)}>Ver o fechamento de {diaDaSemana(s.semana)}</a>
        </p>
      ))}
    </section>
  )
}

/**
 * Troca de fechamento por setas ao lado do título (#25, variação B). A lista vem do mais novo para o mais antigo.
 * O ponto marca o vizinho com aviso: anterior ao atual, com pendência e sem término.
 */
function Setas({ semanas, semana }: { semanas: Semana[]; semana: string }) {
  const i = semanas.findIndex((s) => s.semana === semana)
  if (i === -1) return null
  const anterior = semanas[i + 1]
  const proximo = semanas[i - 1]
  return (
    <nav className="setas" aria-label="Trocar de fechamento">
      <Seta vizinha={anterior} direcao="anterior" />
      <span className="setas-atual" aria-current="page">
        {diaDaSemana(semana)}
      </span>
      <Seta vizinha={proximo} direcao="proximo" />
    </nav>
  )
}

function Seta({ vizinha, direcao }: { vizinha: Semana | undefined; direcao: 'anterior' | 'proximo' }) {
  const seta = direcao === 'anterior' ? '‹' : '›'
  const nome = direcao === 'anterior' ? 'Fechamento anterior' : 'Próximo fechamento'
  if (!vizinha) {
    return (
      <span className="seta" aria-hidden="true" data-desligada>
        {seta}
      </span>
    )
  }
  const data = diaDaSemana(vizinha.semana)
  const marcas = [vizinha.aviso && 'sem término', !vizinha.tem_rodada && 'não calculado'].filter(Boolean)
  return (
    <a
      className="seta"
      href={hashDaSemana(vizinha.semana)}
      aria-label={`${nome}: ${data}${marcas.length ? ` (${marcas.join(', ')})` : ''}`}
      title={marcas.length ? marcas.join(', ') : undefined}
    >
      {direcao === 'anterior' && <span aria-hidden="true">{seta}</span>}
      <span className="seta-data">{data}</span>
      {vizinha.aviso && <span className="ponto" aria-hidden="true" />}
      {direcao === 'proximo' && <span aria-hidden="true">{seta}</span>}
    </a>
  )
}

function Detalhe({
  fechamento,
  dia,
  clienteId,
  lojista,
  acoes,
}: {
  fechamento: Fechamento
  dia: string | null
  clienteId: string
  lojista: boolean
  acoes: Acoes
}) {
  const { resumo, rodada } = fechamento
  const conferir = paraConferir(resumo)
  const conferencia = fechamento.ultima_conferencia
  const conferido = conferencia !== null && !podeConferir(conferencia, rodada.id, resumo)

  return (
    <>
      <AvisoDaConferencia fechamento={fechamento} />

      {/* O resumo é um cartão (#32): a linha, o corte e a trava com o "?", a barra do esperado e o "Marcar como conferido". */}
      <section className="resumo" data-recomendacao={resumo.recomendacao} aria-label="Resumo do fechamento">
        <p className="resumo-linha">
          {linhaDoResumo(resumo)}
          {resumo.itens_falta_de_verdade > 0 && (
            <>
              {' '}
              <Ajuda termo="falta" />
            </>
          )}
        </p>
        <p className="resumo-sub">
          {conferir && (
            <>
              {conferir} <Ajuda termo="conferir" /> ·{' '}
            </>
          )}
          Corte em {quando(rodada.corte)} <Ajuda termo="corte" />
          {resumo.limite_trava_centavos != null && (
            <>
              {' '}
              · Trava em {emReais(resumo.limite_trava_centavos)} <Ajuda termo="trava" />
            </>
          )}
        </p>
        {/* Até quando os números valem (ADR 0011): a última ingestão, não a hora da rodada. */}
        <p className="resumo-atualizacao" data-atrasada={fechamento.atualizacao.atrasada || undefined}>
          {linhaDaAtualizacao(fechamento.atualizacao)}
        </p>
        <BarraDoEsperado fechamento={fechamento} />
        {lojista && (
          <div className="acoes" role="group" aria-label="O que fazer com este fechamento">
            {conferido ? (
              <>
                {/* O estado no lugar do botão (ADR 0012): já vale para a rodada e o resumo que a tela mostra. */}
                <p className="conferido" role="status">
                  <span aria-hidden="true">✓</span> {fraseDoConferido(conferencia)}
                </p>
                <p className="ajuda">Se chegar rodada nova ou o limite mudar o resumo, dá para conferir de novo.</p>
              </>
            ) : (
              <>
                <Conferir clienteId={clienteId} rodadaId={rodada.id} resumo={resumo} acoes={acoes} />
                <p className="ajuda">
                  Registra que você conferiu esta rodada, com o resumo de agora. Não trava nada. O limite da trava
                  fica em <a href={hashDa({ tela: 'limite' })}>Limite</a>.
                </p>
              </>
            )}
          </div>
        )}
      </section>

      <Faixa fechamento={fechamento} dia={dia} />
      <Lista fechamento={fechamento} dia={dia} />
    </>
  )
}

/**
 * A conferência que já não vale para o que a tela mostra: rodada nova, ou o limite mudou o resumo.
 * Mostra o antes e o agora. Quando ela ainda vale, quem e quando ficam no cartão (lojista) e na faixa (suporte).
 */
function AvisoDaConferencia({ fechamento }: { fechamento: Fechamento }) {
  const conferencia = fechamento.ultima_conferencia
  if (!conferencia || !podeConferir(conferencia, fechamento.rodada.id, fechamento.resumo)) return null
  return (
    <div className="conferencia conferencia-mudou" role="status">
      <p>
        <strong>O fechamento mudou desde a última conferência</strong>, em {quando(conferencia.em)}.
      </p>
      <dl>
        <dt>Antes</dt>
        <dd>{linhaDoResumo(conferencia.resumo)}</dd>
        <dt>Agora</dt>
        <dd>{linhaDoResumo(fechamento.resumo)}</dd>
      </dl>
    </div>
  )
}

/**
 * O botão e a confirmação (ADR 0012). O `<dialog>` modal dá o foco preso, o Esc e a volta do foco ao botão;
 * o que foi escolhido chega pelo `returnValue` no `close`.
 */
function Conferir({
  clienteId,
  rodadaId,
  resumo,
  acoes,
}: {
  clienteId: string
  rodadaId: number
  resumo: Fechamento['resumo']
  acoes: Acoes
}) {
  const [enviando, setEnviando] = useState(false)
  const [falhou, setFalhou] = useState(false)
  const dialogo = useRef<HTMLDialogElement>(null)
  const cancelar = useRef<HTMLButtonElement>(null)

  function abrir() {
    setFalhou(false)
    dialogo.current?.showModal()
    // O autoFocus do React só age na montagem, com o diálogo fechado: o foco vai para a saída segura aqui.
    cancelar.current?.focus()
  }

  function aoFechar() {
    const d = dialogo.current
    if (!d) return
    // Esc não define valor e o navegador pode manter o anterior: zera para a próxima vez.
    const escolha = d.returnValue
    d.returnValue = ''
    if (escolha === 'confirmar') void conferir()
  }

  async function conferir() {
    setEnviando(true)
    try {
      // A rodada que a tela mostra, não a mais recente do banco: pode ter chegado outra no meio.
      const resposta = await enviar(`/clientes/${encodeURIComponent(clienteId)}/conferencias`, 'POST', {
        rodada_id: rodadaId,
      })
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

  return (
    <div className="conferir">
      <button type="button" onClick={abrir} disabled={enviando}>
        Marcar como conferido
      </button>
      <p role="status">{falhou ? 'Não foi possível registrar. Tente de novo.' : ''}</p>
      <dialog
        ref={dialogo}
        className="confirmar-conferencia"
        aria-labelledby="confirmar-conferencia-titulo"
        aria-describedby="confirmar-conferencia-aviso"
        onClose={aoFechar}
      >
        <h2 id="confirmar-conferencia-titulo">Marcar este fechamento como conferido?</h2>
        <p>Fica registrado quem conferiu, quando e este resumo:</p>
        <p className="confirmar-conferencia-resumo">{linhaDoResumo(resumo)}</p>
        <p id="confirmar-conferencia-aviso">{avisoDaConfirmacao(resumo)}</p>
        <form method="dialog" className="confirmar-conferencia-botoes">
          <button ref={cancelar} value="cancelar">
            Cancelar
          </button>
          <button value="confirmar" className="primario">
            Confirmar conferência
          </button>
        </form>
      </dialog>
    </div>
  )
}

// O worker leva alguns segundos (ADR 0004). Sem entrada nova a rodada é a mesma, então não dá para esperar por ela:
// a tela recarrega uma vez e mostra o que houver.
const RECARREGAR_DEPOIS_DO_PEDIDO_MS = 5_000

/**
 * Só o suporte vê: a tela embaixo é a da lojista, para os dois olharem a mesma coisa num chamado.
 * Mostra a conferência vista de fora e pede uma rodada nova da semana mostrada.
 */
function FaixaDoSuporte({
  nomeDoCliente,
  clienteId,
  semana,
  fechamento,
  acoes,
}: {
  nomeDoCliente: string
  clienteId: string
  semana: string | null
  fechamento: Fechamento | null
  acoes: Acoes
}) {
  const [pedido, setPedido] = useState<'parado' | 'enviando' | 'enviado' | 'falhou'>('parado')
  const relogio = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => () => clearTimeout(relogio.current), [])

  async function pedirRodadaNova() {
    if (semana === null) return
    setPedido('enviando')
    try {
      const resposta = await enviar(`/clientes/${encodeURIComponent(clienteId)}/reprocessar`, 'POST', { semana })
      if (resposta.status === 401) return acoes.aoPerderSessao()
      if (!resposta.ok) return setPedido('falhou')
      setPedido('enviado')
      clearTimeout(relogio.current)
      relogio.current = setTimeout(acoes.recarregar, RECARREGAR_DEPOIS_DO_PEDIDO_MS)
    } catch (erro: unknown) {
      console.error(erro)
      setPedido('falhou')
    }
  }

  return (
    <section className="faixa-do-suporte" aria-label="Visão do suporte">
      <div className="faixa-do-suporte-texto">
        <p>
          <strong>{fraseDaFaixa(nomeDoCliente)}</strong>
        </p>
        {fechamento && <p>{fraseDaConferencia(fechamento.ultima_conferencia, fechamento.rodada.id)}</p>}
      </div>
      {/* O reprocessamento só existe para semana com rodada; antes dela, a tela já pede o cálculo. */}
      {fechamento && (
        <div className="faixa-do-suporte-acao">
          <button type="button" onClick={pedirRodadaNova} disabled={pedido === 'enviando'}>
            Pedir rodada nova
          </button>
          <p role="status">
            {pedido === 'enviado' ? PEDIDO_ENVIADO : pedido === 'falhou' ? 'Não foi possível pedir. Tente de novo.' : ''}
          </p>
        </div>
      )}
    </section>
  )
}
