import { useEffect, useState } from 'react'
import type { components } from '../api'
import { type Acoes, enviar } from '../enviar'
import { hashDa, hashDaSemana } from '../navegacao'
import { DetalheDoItem } from './DetalheDoItem'
import { Faixa, Lista } from './Lista'
import { useVariante } from '../prototipo/variante'
import { VarianteA } from '../prototipo/VarianteA'
import { VarianteB } from '../prototipo/VarianteB'
import {
  type Fechamento,
  type Semana,
  diaDaSemana,
  linhaDoResumo,
  paraConferir,
  quando,
  textoDoAviso,
} from './textos'

type Papel = components['schemas']['Papel']

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
  papel,
  escolhida,
  dia,
  item,
  aoPerderSessao,
}: {
  clienteId: string
  papel: Papel
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
                // Só a lojista muda o limite e marca "Terminei" (ADR 0005); o suporte só olha.
                lojista={papel === 'lojista'}
                acoes={acoes}
              />
            )
        }
      })()}
    </>
  )
}

/** Fechamentos anteriores ao atual com pendência e sem "Terminei". Lê os términos; não é estado (ADR 0003). */
function Avisos({ semanas }: { semanas: Semana[] }) {
  const comAviso = semanas.filter((s) => s.aviso)
  if (comAviso.length === 0) return null
  return (
    <section className="avisos" aria-label="Fechamentos sem término">
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
  const variante = useVariante()

  // PROTÓTIPO (Q5c): as variantes recebem o "Terminei" pronto e desenham o resto.
  if (variante !== 'atual') {
    const acoesDaVariante = lojista && (
      <section className="acoes" aria-label="O que fazer com este fechamento">
        <Terminei clienteId={clienteId} rodadaId={rodada.id} acoes={acoes} />
        <p className="ajuda">Registra que você conferiu esta rodada. Não trava nada.</p>
      </section>
    )
    // C: a estrutura e os gráficos da A, com a paleta e as abas de severidade da B.
    return (
      <>
        <AvisoDoTermino fechamento={fechamento} />
        {variante === 'B' ? (
          <VarianteB fechamento={fechamento} dia={dia} acoes={acoesDaVariante} />
        ) : (
          <VarianteA fechamento={fechamento} dia={dia} acoes={acoesDaVariante} abas={variante === 'C'} />
        )}
      </>
    )
  }

  return (
    <>
      <AvisoDoTermino fechamento={fechamento} />

      <header className="resumo" data-recomendacao={resumo.recomendacao}>
        <p className="resumo-linha">{linhaDoResumo(resumo)}</p>
        {conferir && <p className="resumo-conferir">{conferir}</p>}
        <p className="resumo-corte">Fechamento com corte em {quando(rodada.corte)}</p>
      </header>

      {lojista && (
        <section className="acoes" aria-label="O que fazer com este fechamento">
          <Terminei clienteId={clienteId} rodadaId={rodada.id} acoes={acoes} />
          <p className="ajuda">
            Registra que você conferiu esta rodada. Não trava nada. O limite da trava fica em{' '}
            <a href={hashDa({ tela: 'limite' })}>Limite</a>.
          </p>
        </section>
      )}

      <Faixa fechamento={fechamento} dia={dia} />
      <Lista fechamento={fechamento} dia={dia} />
    </>
  )
}

/** O "Terminei" mais recente: na mesma rodada só informa; com rodada nova, mostra o antes e o agora. */
function AvisoDoTermino({ fechamento }: { fechamento: Fechamento }) {
  const termino = fechamento.ultimo_termino
  if (!termino) return null
  if (termino.rodada_id === fechamento.rodada.id) {
    return (
      <p className="termino" role="status">
        {termino.quem} terminou este fechamento em {quando(termino.em)}.
      </p>
    )
  }
  return (
    <div className="termino termino-mudou" role="status">
      <p>
        <strong>O fechamento mudou desde que você terminou</strong> em {quando(termino.em)}.
      </p>
      <dl>
        <dt>Antes</dt>
        <dd>{linhaDoResumo(termino.resumo)}</dd>
        <dt>Agora</dt>
        <dd>{linhaDoResumo(fechamento.resumo)}</dd>
      </dl>
    </div>
  )
}

function Terminei({ clienteId, rodadaId, acoes }: { clienteId: string; rodadaId: number; acoes: Acoes }) {
  const [enviando, setEnviando] = useState(false)
  const [falhou, setFalhou] = useState(false)

  async function terminar() {
    setEnviando(true)
    setFalhou(false)
    try {
      // A rodada que a tela mostra, não a mais recente do banco: pode ter chegado outra no meio.
      const resposta = await enviar(`/clientes/${encodeURIComponent(clienteId)}/terminei`, 'POST', {
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
    <div className="terminei">
      <button type="button" onClick={terminar} disabled={enviando}>
        Terminei
      </button>
      <p role="status">{falhou ? 'Não foi possível registrar. Tente de novo.' : ''}</p>
    </div>
  )
}
