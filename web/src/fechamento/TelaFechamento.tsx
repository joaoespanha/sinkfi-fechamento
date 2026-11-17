import { type FormEvent, useEffect, useId, useState } from 'react'
import type { components } from '../api'
import {
  type Fechamento,
  type Item,
  campoDosCentavos,
  centavosDoCampo,
  emReais,
  explicacaoDoMotivo,
  linhaDoCredito,
  linhaDoRecebivel,
  linhaDoResumo,
  origem,
  paraConferir,
  quando,
  textoDaSeveridade,
  textoDoMotivo,
} from './textos'

type Papel = components['schemas']['Papel']

type Estado =
  | { tipo: 'carregando' }
  | { tipo: 'sem_rodada' }
  | { tipo: 'erro' }
  | { tipo: 'pronto'; fechamento: Fechamento }

type Pendencia = Item & {
  severidade: NonNullable<Item['severidade']>
  motivo: NonNullable<Item['motivo']>
  pendencia_centavos: number
}

/** O que a tela faz depois de uma escrita: 401 volta ao login, sucesso recarrega o fechamento. */
type Acoes = { aoPerderSessao: () => void; recarregar: () => void }

function pendencias(itens: Item[]): Pendencia[] {
  return itens
    .filter((i): i is Pendencia => i.severidade != null && i.motivo != null && i.pendencia_centavos != null)
    // Faltas de verdade primeiro; dentro de cada severidade, o maior valor primeiro.
    .sort(
      (a, b) =>
        Number(a.severidade !== 'falta_de_verdade') - Number(b.severidade !== 'falta_de_verdade') ||
        b.pendencia_centavos - a.pendencia_centavos,
    )
}

async function enviar(caminho: string, metodo: 'PUT' | 'POST', corpo: unknown): Promise<Response> {
  return fetch(`/api${caminho}`, {
    method: metodo,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo),
  })
}

export function TelaFechamento({
  clienteId,
  papel,
  aoPerderSessao,
}: {
  clienteId: string
  papel: Papel
  // 401: o token venceu (8 horas) ou o usuário foi desativado. A tela volta ao login.
  aoPerderSessao: () => void
}) {
  const [estado, setEstado] = useState<Estado>({ tipo: 'carregando' })
  // Muda depois de cada escrita para buscar o fechamento de novo, sem voltar a "carregando".
  const [versao, setVersao] = useState(0)

  useEffect(() => {
    const controle = new AbortController()
    fetch(`/api/clientes/${encodeURIComponent(clienteId)}/fechamento`, { signal: controle.signal })
      .then(async (resposta) => {
        if (resposta.status === 401) return aoPerderSessao()
        // 404 também é cliente de outro dono ou inexistente (ADR 0005).
        if (resposta.status === 404) return setEstado({ tipo: 'sem_rodada' })
        if (!resposta.ok) return setEstado({ tipo: 'erro' })
        setEstado({ tipo: 'pronto', fechamento: (await resposta.json()) as Fechamento })
      })
      .catch((erro: unknown) => {
        if (!controle.signal.aborted) {
          console.error(erro)
          setEstado({ tipo: 'erro' })
        }
      })
    return () => controle.abort()
  }, [clienteId, aoPerderSessao, versao])

  const acoes: Acoes = { aoPerderSessao, recarregar: () => setVersao((v) => v + 1) }

  switch (estado.tipo) {
    case 'carregando':
      return <p aria-busy="true">Carregando o fechamento…</p>
    case 'sem_rodada':
      return <p>Ainda não há fechamento calculado.</p>
    case 'erro':
      return <p role="alert">Não foi possível carregar o fechamento. Tente de novo em instantes.</p>
    case 'pronto':
      return (
        <Detalhe
          fechamento={estado.fechamento}
          clienteId={clienteId}
          // Só a lojista muda o limite e marca "Terminei" (ADR 0005); o suporte só olha.
          lojista={papel === 'lojista'}
          acoes={acoes}
        />
      )
  }
}

function Detalhe({
  fechamento,
  clienteId,
  lojista,
  acoes,
}: {
  fechamento: Fechamento
  clienteId: string
  lojista: boolean
  acoes: Acoes
}) {
  const { resumo, rodada } = fechamento
  const conferir = paraConferir(resumo)
  const lista = pendencias(fechamento.itens)

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
          <FormularioLimite clienteId={clienteId} limite={resumo.limite_trava_centavos} acoes={acoes} />
        </section>
      )}

      {lista.length > 0 && (
        <div className="tabela" role="region" aria-labelledby="pendencias-titulo" tabIndex={0}>
          <table>
            <caption id="pendencias-titulo">Pendências</caption>
            <thead>
              <tr>
                <th scope="col">Motivo</th>
                <th scope="col">Severidade</th>
                <th scope="col">Origem</th>
                <th scope="col" className="valor">
                  Valor
                </th>
              </tr>
            </thead>
            <tbody>
              {lista.map((p, i) => (
                <tr key={i} data-severidade={p.severidade}>
                  <th scope="row">
                    <Explicacao pendencia={p} />
                  </th>
                  <td>{textoDaSeveridade(p.severidade)}</td>
                  <td>{origem(p)}</td>
                  <td className="valor">{emReais(p.pendencia_centavos)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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

function FormularioLimite({
  clienteId,
  limite,
  acoes,
}: {
  clienteId: string
  limite: number | null
  acoes: Acoes
}) {
  const id = useId()
  const [texto, setTexto] = useState(campoDosCentavos(limite))
  const [mensagem, setMensagem] = useState('')
  const [invalido, setInvalido] = useState(false)
  const [enviando, setEnviando] = useState(false)

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const centavos = centavosDoCampo(texto)
    if (centavos === 'invalido') {
      setInvalido(true)
      setMensagem('Digite o valor em reais, como 2.000 ou 2000,50.')
      document.getElementById(`${id}-campo`)?.focus()
      return
    }
    setInvalido(false)
    setEnviando(true)
    try {
      const resposta = await enviar(`/clientes/${encodeURIComponent(clienteId)}/limite`, 'PUT', {
        limite_trava_centavos: centavos,
      })
      if (resposta.status === 401) return acoes.aoPerderSessao()
      if (!resposta.ok) return setMensagem('Não foi possível salvar o limite. Tente de novo.')
      setMensagem(centavos === null ? 'Trava desligada.' : `Limite salvo: ${emReais(centavos)}.`)
      acoes.recarregar()
    } catch (erro: unknown) {
      console.error(erro)
      setMensagem('Não foi possível salvar o limite. Tente de novo.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="limite" onSubmit={salvar} noValidate>
      <label htmlFor={`${id}-campo`}>Limite da trava (R$)</label>
      <input
        id={`${id}-campo`}
        name="limite"
        type="text"
        inputMode="decimal"
        autoComplete="off"
        enterKeyHint="done"
        value={texto}
        aria-invalid={invalido}
        aria-describedby={`${id}-ajuda ${id}-mensagem`}
        onChange={(e) => {
          setTexto(e.target.value)
          if (invalido) setInvalido(false)
        }}
      />
      <p id={`${id}-ajuda`} className="ajuda">
        Acima deste valor em faltas, o resumo recomenda não fechar. Deixe vazio para desligar a trava.
      </p>
      <button type="submit" disabled={enviando}>
        Salvar limite
      </button>
      <p id={`${id}-mensagem`} role="status">
        {mensagem}
      </p>
    </form>
  )
}

/** Do grupo até o recebível, o crédito e o motivo da regra. Sai inteira do que a rodada gravou. */
function Explicacao({ pendencia: p }: { pendencia: Pendencia }) {
  const grupo = p.esperado_centavos !== null
  return (
    <details className="explicacao">
      <summary>{textoDoMotivo(p.motivo)}</summary>
      <p>{explicacaoDoMotivo(p.motivo)}</p>
      {grupo && (
        <dl className="valores">
          <dt>Esperado</dt>
          <dd>{emReais(p.esperado_centavos ?? 0)}</dd>
          <dt>Caiu</dt>
          <dd>{emReais(p.caiu_centavos ?? 0)}</dd>
          <dt>Não caiu</dt>
          <dd>{emReais(p.nao_caiu_centavos ?? 0)}</dd>
          <dt>Próximo fechamento</dt>
          <dd>{emReais(p.proximo_fechamento_centavos ?? 0)}</dd>
        </dl>
      )}
      {p.recebiveis.length > 0 && (
        <>
          <p className="explicacao-titulo">Recebíveis</p>
          <ul>
            {p.recebiveis.map((r) => (
              <li key={r.id}>
                {linhaDoRecebivel(r)} · <span className="valor">{emReais(r.liquido_centavos)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="explicacao-titulo">Créditos</p>
      {p.creditos.length > 0 ? (
        <ul>
          {p.creditos.map((c) => (
            <li key={c.id}>
              {linhaDoCredito(c)} · <span className="valor">{emReais(c.valor_centavos)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p>Nenhum crédito casou com este grupo.</p>
      )}
    </details>
  )
}
