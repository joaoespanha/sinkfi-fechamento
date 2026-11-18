import type { components } from '../api'

export type ClienteEncontrado = components['schemas']['ClienteEncontradoLido']

// O mesmo mínimo da api: abaixo disso ela responde 422.
const MINIMO = 3

/** O termo que vai à api, ou null se ainda é curto demais para buscar. */
export function termoBuscavel(texto: string): string | null {
  const termo = texto.trim()
  return termo.length >= MINIMO ? termo : null
}

function comPontuacao(documento: string): string {
  const partes = /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/.exec(documento)
  return partes ? `${partes[1]}.${partes[2]}.${partes[3]}/${partes[4]}-${partes[5]}` : documento
}

/** A linha de baixo de cada resultado: as lojas e os CNPJs, sem repetir o CNPJ que duas lojas dividem. */
export function descreverLojas(cliente: ClienteEncontrado): string {
  if (cliente.lojas.length === 0) return 'Sem lojas cadastradas'
  const nomes = cliente.lojas.map((loja) => loja.nome).join(', ')
  const cnpjs = [...new Set(cliente.lojas.map((loja) => comPontuacao(loja.documento)))].join(', ')
  return `${nomes} · CNPJ ${cnpjs}`
}

// O mesmo limite da api: com a lista cheia, pode haver cliente cortado.
const LIMITE = 10

export function avisoDaBusca(quantos: number): string | null {
  if (quantos === 0) return 'Nenhum cliente encontrado.'
  if (quantos >= LIMITE) return `Mostrando os ${LIMITE} primeiros. Use um termo mais específico.`
  return null
}

/** null = sem sessão (401). */
export async function buscarClientes(termo: string): Promise<ClienteEncontrado[] | null> {
  const resposta = await fetch(`/api/clientes?${new URLSearchParams({ busca: termo })}`)
  if (resposta.status === 401) return null
  if (!resposta.ok) throw new Error(`/clientes respondeu ${resposta.status}`)
  return (await resposta.json()) as ClienteEncontrado[]
}
