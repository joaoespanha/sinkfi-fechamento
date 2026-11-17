import { TelaFechamento } from './fechamento/TelaFechamento'

// O cliente da demonstração (`semear`). Com o login (#9), ele vem da sessão.
const CLIENTE = 'cli_marina'

export default function App() {
  return (
    <main>
      <h1>Fechamento da semana</h1>
      <TelaFechamento clienteId={CLIENTE} />
    </main>
  )
}
