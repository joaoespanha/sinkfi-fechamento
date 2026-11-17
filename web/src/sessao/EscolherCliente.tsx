import { type FormEvent } from 'react'

/** Só o suporte vê: digita o id do cliente. Não há listagem de clientes (ADR 0005). */
export function EscolherCliente({ aoEscolher }: { aoEscolher: (clienteId: string) => void }) {
  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const id = String(new FormData(evento.currentTarget).get('cliente')).trim()
    if (id) aoEscolher(id)
  }

  return (
    <form className="escolher-cliente" onSubmit={enviar}>
      <label htmlFor="cliente">Id do cliente</label>
      <input id="cliente" name="cliente" type="text" spellCheck={false} autoCapitalize="off" required />
      <button type="submit">Abrir</button>
    </form>
  )
}
