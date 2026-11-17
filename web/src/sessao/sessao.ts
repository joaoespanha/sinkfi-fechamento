import type { components } from '../api'

export type Eu = components['schemas']['EuResposta']
type LoginEntrada = components['schemas']['LoginEntrada']

/** null = sem sessão (401): a tela mostra o login. */
export async function quemSouEu(): Promise<Eu | null> {
  const resposta = await fetch('/api/eu')
  if (resposta.status === 401) return null
  if (!resposta.ok) throw new Error(`/eu respondeu ${resposta.status}`)
  return (await resposta.json()) as Eu
}

export type ResultadoLogin = 'ok' | 'recusado' | 'erro'

export async function entrar(entrada: LoginEntrada): Promise<ResultadoLogin> {
  const resposta = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entrada),
  })
  if (resposta.ok) return 'ok'
  // 401 é credencial errada; 429 é o limite do nginx no login.
  return resposta.status === 401 ? 'recusado' : 'erro'
}

export async function sair(): Promise<void> {
  await fetch('/api/logout', { method: 'POST' })
}
