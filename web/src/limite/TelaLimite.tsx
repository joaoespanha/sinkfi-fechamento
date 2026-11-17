import { type FormEvent, useEffect, useId, useState } from 'react'
import type { components } from '../api'
import { type Acoes, enviar } from '../enviar'
import { campoDosCentavos, centavosDoCampo, emReais } from '../fechamento/textos'

type Limite = components['schemas']['LimiteLido']

type Estado = { tipo: 'carregando' } | { tipo: 'erro' } | { tipo: 'pronto'; limite: number | null }

/** O limite da trava (#25). Só a lojista muda; o suporte vê o valor (ADR 0005). */
export function TelaLimite({
  clienteId,
  lojista,
  aoPerderSessao,
}: {
  clienteId: string
  lojista: boolean
  aoPerderSessao: () => void
}) {
  const [estado, setEstado] = useState<Estado>({ tipo: 'carregando' })
  // Muda depois de salvar para ler o limite de novo, sem voltar a "carregando".
  const [versao, setVersao] = useState(0)

  useEffect(() => {
    const controle = new AbortController()
    fetch(`/api/clientes/${encodeURIComponent(clienteId)}/limite`, { signal: controle.signal })
      .then(async (resposta) => {
        if (resposta.status === 401) return aoPerderSessao()
        if (!resposta.ok) return setEstado({ tipo: 'erro' })
        setEstado({ tipo: 'pronto', limite: ((await resposta.json()) as Limite).limite_trava_centavos })
      })
      .catch((erro: unknown) => {
        if (!controle.signal.aborted) {
          console.error(erro)
          setEstado({ tipo: 'erro' })
        }
      })
    return () => controle.abort()
  }, [clienteId, aoPerderSessao, versao])

  return (
    <>
      <header className="titulo">
        <h1>Limite da trava</h1>
      </header>
      {estado.tipo === 'carregando' && <p aria-busy="true">Carregando o limite…</p>}
      {estado.tipo === 'erro' && <p role="alert">Não foi possível carregar o limite. Tente de novo em instantes.</p>}
      {estado.tipo === 'pronto' &&
        (lojista ? (
          <FormularioLimite
            clienteId={clienteId}
            limite={estado.limite}
            acoes={{ aoPerderSessao, recarregar: () => setVersao((v) => v + 1) }}
          />
        ) : (
          <div className="limite-leitura">
            <p className="limite-valor">
              {estado.limite === null ? 'Trava desligada' : emReais(estado.limite)}
            </p>
            <p className="ajuda">Só a lojista muda o limite.</p>
          </div>
        ))}
    </>
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
