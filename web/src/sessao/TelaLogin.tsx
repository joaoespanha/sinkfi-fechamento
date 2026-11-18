import { type FormEvent, useState } from 'react'
import { entrar } from './sessao'

const MENSAGENS = {
  recusado: 'E-mail ou senha incorretos.',
  erro: 'Não foi possível entrar agora. Tente de novo em instantes.',
} as const

export function TelaLogin({ aoEntrar }: { aoEntrar: () => void }) {
  const [enviando, setEnviando] = useState(false)
  const [falha, setFalha] = useState<keyof typeof MENSAGENS | null>(null)

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const dados = new FormData(evento.currentTarget)
    setEnviando(true)
    setFalha(null)
    try {
      const resultado = await entrar({ email: String(dados.get('email')), senha: String(dados.get('senha')) })
      if (resultado === 'ok') return aoEntrar()
      setFalha(resultado)
    } catch (erro) {
      console.error(erro)
      setFalha('erro')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="login" onSubmit={enviar} aria-describedby={falha ? 'login-falha' : undefined}>
      <h2>Entrar na sinkfi</h2>
      <p className="login-sub">Use o e-mail e a senha da sua conta.</p>
      <label htmlFor="email">E-mail</label>
      <input id="email" name="email" type="email" autoComplete="username" spellCheck={false} required />
      <label htmlFor="senha">Senha</label>
      <input
        id="senha"
        name="senha"
        type="password"
        autoComplete="current-password"
        enterKeyHint="done"
        required
      />
      {/* Sempre no DOM: o leitor de tela anuncia quando o texto muda. */}
      <p id="login-falha" className="login-falha" role="alert">
        {falha && MENSAGENS[falha]}
      </p>
      <button type="submit" disabled={enviando}>
        {enviando ? 'Entrando…' : 'Entrar'}
      </button>
    </form>
  )
}
