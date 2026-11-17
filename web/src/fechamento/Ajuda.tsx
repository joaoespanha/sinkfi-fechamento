import { useId } from 'react'
import { TERMOS, type Termo } from './textos'

/**
 * O "?" ao lado de um termo (#32): abre a definição num popover nativo, sem JavaScript próprio.
 * Clicar fora ou apertar Esc fecha. O CSS ancora a caixa ao botão onde há anchor positioning;
 * nos outros navegadores ela abre no meio da tela, que é o padrão do popover.
 */
export function Ajuda({ termo }: { termo: Termo }) {
  const id = useId()
  const { nome, texto } = TERMOS[termo]
  return (
    <>
      <button type="button" className="ajuda-botao" popoverTarget={id} aria-label={`O que é ${nome}?`}>
        ?
      </button>
      <span id={id} popover="auto" className="ajuda-caixa" role="note">
        <strong>{nome}</strong> {texto}
      </span>
    </>
  )
}
