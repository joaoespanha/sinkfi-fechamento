import { useCallback, useEffect, useState } from 'react'
import { TelaFechamento } from './fechamento/TelaFechamento'
import { EscolherCliente } from './sessao/EscolherCliente'
import { type Eu, quemSouEu, sair } from './sessao/sessao'
import { TelaLogin } from './sessao/TelaLogin'

type Estado = { tipo: 'carregando' } | { tipo: 'sem_sessao' } | { tipo: 'erro' } | { tipo: 'logado'; eu: Eu }

export default function App() {
  const [estado, setEstado] = useState<Estado>({ tipo: 'carregando' })
  // Só o suporte escolhe; a lojista sempre vê o próprio cliente.
  const [clienteDoSuporte, setClienteDoSuporte] = useState<string | null>(null)

  const carregar = useCallback(() => {
    quemSouEu()
      .then((eu) => setEstado(eu ? { tipo: 'logado', eu } : { tipo: 'sem_sessao' }))
      .catch((erro: unknown) => {
        console.error(erro)
        setEstado({ tipo: 'erro' })
      })
  }, [])

  useEffect(carregar, [carregar])

  const perdeuSessao = useCallback(() => {
    setClienteDoSuporte(null)
    setEstado({ tipo: 'sem_sessao' })
  }, [])

  async function encerrar() {
    await sair()
    perdeuSessao()
  }

  return (
    <main>
      <h1>Fechamento da semana</h1>
      {estado.tipo === 'carregando' && <p aria-busy="true">Carregando…</p>}
      {estado.tipo === 'erro' && <p role="alert">Não foi possível carregar. Tente de novo em instantes.</p>}
      {estado.tipo === 'sem_sessao' && <TelaLogin aoEntrar={carregar} />}
      {estado.tipo === 'logado' && (
        <>
          <p className="sessao">
            {estado.eu.email}
            <button type="button" onClick={encerrar}>
              Sair
            </button>
          </p>
          {estado.eu.papel === 'lojista' && estado.eu.cliente_id && (
            <TelaFechamento clienteId={estado.eu.cliente_id} aoPerderSessao={perdeuSessao} />
          )}
          {estado.eu.papel === 'suporte' && (
            <>
              <EscolherCliente aoEscolher={setClienteDoSuporte} />
              {clienteDoSuporte && (
                // A key recria a tela ao trocar de cliente: volta a "carregando" sem resto do anterior.
                <TelaFechamento key={clienteDoSuporte} clienteId={clienteDoSuporte} aoPerderSessao={perdeuSessao} />
              )}
            </>
          )}
        </>
      )}
    </main>
  )
}
