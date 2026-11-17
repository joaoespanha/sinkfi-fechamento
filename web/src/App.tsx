import { useCallback, useEffect, useState } from 'react'
import { TelaFechamento } from './fechamento/TelaFechamento'
import { TelaLimite } from './limite/TelaLimite'
import { type Rota, hashDa, useRota } from './navegacao'
import { EscolherCliente } from './sessao/EscolherCliente'
import { type Eu, quemSouEu, sair } from './sessao/sessao'
import { TelaLogin } from './sessao/TelaLogin'

type Estado = { tipo: 'carregando' } | { tipo: 'sem_sessao' } | { tipo: 'erro' } | { tipo: 'logado'; eu: Eu }

export default function App() {
  const [estado, setEstado] = useState<Estado>({ tipo: 'carregando' })
  // Só o suporte escolhe; a lojista sempre vê o próprio cliente.
  const [clienteDoSuporte, setClienteDoSuporte] = useState<string | null>(null)
  const rota = useRota()

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

  if (estado.tipo !== 'logado') {
    return (
      <main className="sozinha">
        <h1>Fechamento da semana</h1>
        {estado.tipo === 'carregando' && <p aria-busy="true">Carregando…</p>}
        {estado.tipo === 'erro' && <p role="alert">Não foi possível carregar. Tente de novo em instantes.</p>}
        {estado.tipo === 'sem_sessao' && <TelaLogin aoEntrar={carregar} />}
      </main>
    )
  }

  const { eu } = estado
  const lojista = eu.papel === 'lojista'
  const clienteId = lojista ? eu.cliente_id : clienteDoSuporte

  return (
    <div className="app">
      <aside className="lateral">
        <span className="marca">sinkfi</span>
        <div className="cliente">
          <span className="rotulo">Cliente</span>
          {/* A lojista vê o dela fixo; o suporte digita o id (ADR 0005). */}
          {lojista ? (
            <span>{eu.cliente_id}</span>
          ) : (
            <EscolherCliente atual={clienteDoSuporte} aoEscolher={setClienteDoSuporte} />
          )}
        </div>
        <nav className="paginas" aria-label="Páginas">
          <LinkDaPagina rota={rota} para={{ tela: 'fechamento', semana: null, dia: null, item: null }}>
            Fechamento
          </LinkDaPagina>
          <LinkDaPagina rota={rota} para={{ tela: 'limite' }}>
            Limite
          </LinkDaPagina>
        </nav>
        <div className="rodape">
          <span className="rodape-email">{eu.email}</span>
          <button type="button" onClick={encerrar}>
            Sair
          </button>
        </div>
      </aside>
      <main className="conteudo">
        {clienteId === null ? (
          <p>Escolha um cliente para ver o fechamento.</p>
        ) : rota.tela === 'limite' ? (
          // A key recria a tela ao trocar de cliente: volta a "carregando" sem resto do anterior.
          <TelaLimite key={clienteId} clienteId={clienteId} lojista={lojista} aoPerderSessao={perdeuSessao} />
        ) : (
          <TelaFechamento
            key={clienteId}
            clienteId={clienteId}
            papel={eu.papel}
            escolhida={rota.semana}
            dia={rota.dia}
            item={rota.item}
            aoPerderSessao={perdeuSessao}
          />
        )}
      </main>
    </div>
  )
}

function LinkDaPagina({ rota, para, children }: { rota: Rota; para: Rota; children: string }) {
  return (
    <a href={hashDa(para)} aria-current={rota.tela === para.tela ? 'page' : undefined}>
      {children}
    </a>
  )
}
