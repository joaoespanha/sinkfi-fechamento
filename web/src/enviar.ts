/** O que a tela faz depois de uma escrita: 401 volta ao login, sucesso recarrega o que ela mostra. */
export type Acoes = { aoPerderSessao: () => void; recarregar: () => void }

export async function enviar(caminho: string, metodo: 'PUT' | 'POST', corpo: unknown): Promise<Response> {
  return fetch(`/api${caminho}`, {
    method: metodo,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo),
  })
}
