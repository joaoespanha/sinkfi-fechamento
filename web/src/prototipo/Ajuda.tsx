// PROTÓTIPO (Q7a): o "?" ao lado de um termo abre a definição do GLOSSARY.md, num popover nativo.
// Textos novos: precisam do ok do usuário antes de irem para o textos.ts.
import { useId } from 'react'

export const TERMOS = {
  corte: 'O momento que separa um fechamento do seguinte. O seu é segunda às 18:00, horário de São Paulo. O que cai depois entra no fechamento seguinte.',
  esperado: 'A soma das vendas com liquidação prevista até o dia do fechamento. Esperado = Caiu + Não caiu + Próximo fechamento.',
  caiu: 'A parte do esperado que entrou na conta até o corte e não foi desfeita por chargeback.',
  naoCaiu: 'A parte do esperado que não está na conta: não foi depositada, foi depositada em parte ou saiu por chargeback.',
  proximo: 'A parte do esperado que caiu depois do corte. Não é pendência: entra no fechamento seguinte.',
  falta: 'Dinheiro que muda o fechamento: não entrou, ou entrou e não é seu. É o que pesa na recomendação.',
  conferir: 'Vale olhar, mas não muda o fechamento, como um crédito que não casa com nenhuma venda.',
  trava: 'O limite que você define sobre a soma das faltas de verdade. Acima dele, a recomendação é não fechar. Nunca impede de fechar.',
} as const

export function Ajuda({ termo, nome }: { termo: keyof typeof TERMOS; nome: string }) {
  const id = useId()
  return (
    <>
      <button type="button" className="p-ajuda" popoverTarget={id} aria-label={`O que é ${nome}?`}>
        ?
      </button>
      <span id={id} popover="auto" className="p-ajuda-caixa" role="note">
        <strong>{nome}</strong> {TERMOS[termo]}
      </span>
    </>
  )
}
