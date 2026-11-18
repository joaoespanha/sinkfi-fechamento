import { type FormEvent, useRef, useState } from 'react'
import { avisoDaBusca, buscarClientes, type ClienteEncontrado, descreverLojas, termoBuscavel } from './busca'

type Estado =
  | { tipo: 'parado' }
  | { tipo: 'curto' }
  | { tipo: 'buscando' }
  | { tipo: 'erro' }
  | { tipo: 'pronto'; clientes: ClienteEncontrado[] }

/** Só o suporte vê: acha o cliente pelo e-mail da lojista, pelo CNPJ ou pelo nome (ADR 0010). */
export function EscolherCliente({
  aoEscolher,
  aoPerderSessao,
}: {
  aoEscolher: (clienteId: string) => void
  aoPerderSessao: () => void
}) {
  const [estado, setEstado] = useState<Estado>({ tipo: 'parado' })
  const [aberto, setAberto] = useState<string | null>(null)
  const formulario = useRef<HTMLFormElement>(null)

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const termo = termoBuscavel(String(new FormData(evento.currentTarget).get('busca')))
    if (termo === null) return setEstado({ tipo: 'curto' })
    setEstado({ tipo: 'buscando' })
    try {
      const clientes = await buscarClientes(termo)
      if (clientes === null) return aoPerderSessao()
      setEstado({ tipo: 'pronto', clientes })
    } catch (erro: unknown) {
      console.error(erro)
      setEstado({ tipo: 'erro' })
    }
  }

  function escolher(cliente: ClienteEncontrado) {
    setAberto(cliente.nome)
    setEstado({ tipo: 'parado' })
    formulario.current?.reset()
    aoEscolher(cliente.id)
  }

  const aviso = estado.tipo === 'pronto' ? avisoDaBusca(estado.clientes.length) : null

  return (
    <div className="escolher-cliente">
      {aberto !== null && <span className="cliente-aberto">{aberto}</span>}
      <form ref={formulario} role="search" onSubmit={enviar}>
        <label htmlFor="busca-cliente" className="so-leitor">
          E-mail, CNPJ ou nome do cliente
        </label>
        <input
          id="busca-cliente"
          name="busca"
          type="search"
          placeholder="E-mail, CNPJ ou nome"
          spellCheck={false}
          autoCapitalize="off"
        />
        <button type="submit" disabled={estado.tipo === 'buscando'}>
          Buscar
        </button>
      </form>
      <div aria-live="polite">
        {estado.tipo === 'buscando' && <p className="busca-aviso">Buscando…</p>}
        {estado.tipo === 'curto' && <p className="busca-aviso">Digite ao menos 3 caracteres.</p>}
        {estado.tipo === 'erro' && <p className="busca-aviso">Não foi possível buscar. Tente de novo.</p>}
        {estado.tipo === 'pronto' && (
          <>
            {estado.clientes.length > 0 && (
              <ul className="busca-resultados">
                {estado.clientes.map((cliente) => (
                  <li key={cliente.id}>
                    <button type="button" onClick={() => escolher(cliente)}>
                      <span className="busca-nome">{cliente.nome}</span>
                      <span className="busca-lojas">{descreverLojas(cliente)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {aviso !== null && <p className="busca-aviso">{aviso}</p>}
          </>
        )}
      </div>
    </div>
  )
}
