import type { components } from '../api'

type Esquemas = components['schemas']
export type Fechamento = Esquemas['FechamentoResposta']
export type Item = Esquemas['ItemLido']
type Resumo = Esquemas['ResumoLido']

const dia = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', timeZone: 'America/Sao_Paulo' })
const reais = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export function emReais(centavos: number): string {
  return reais.format(centavos / 100)
}

function itens(n: number): string {
  return n === 1 ? '1 item' : `${n} itens`
}

/** A linha do resumo (GLOSSARY: Resumo). O `switch` é exaustivo: uma recomendação nova não compila. */
export function linhaDoResumo(resumo: Resumo): string {
  const falta = emReais(resumo.falta_de_verdade_centavos)
  const limite = resumo.limite_trava_centavos
  switch (resumo.recomendacao) {
    case 'pode_fechar':
      // Com a trava ligada, pode fechar mesmo com faltas, se a soma ficar dentro do limite.
      return resumo.itens_falta_de_verdade === 0 || limite === null
        ? 'Pode fechar'
        : `Pode fechar: faltam ${falta}, dentro do seu limite de ${emReais(limite)}`
    case 'faltam':
      return `Faltam ${falta} em ${itens(resumo.itens_falta_de_verdade)}`
    case 'nao_feche':
      // `nao_feche` só existe com a trava ligada; o `?? 0` é só para o tipo.
      return `Não feche: faltam ${falta}, acima do seu limite de ${emReais(limite ?? 0)}`
  }
}

export function paraConferir(resumo: Resumo): string | null {
  const n = resumo.itens_para_conferir
  return n === 0 ? null : `${itens(n)} para conferir`
}

export function textoDoMotivo(motivo: Esquemas['Motivo']): string {
  switch (motivo) {
    case 'nao_caiu':
      return 'Não caiu'
    case 'caiu_em_parte':
      return 'Caiu em parte'
    case 'grupo_nao_fecha':
      return 'Grupo não fecha'
    case 'chargeback':
      return 'Chargeback'
    case 'venda_cancelada':
      return 'Venda cancelada'
    case 'entrada_sem_recebivel':
      return 'Entrada sem recebível'
    case 'pode_ser_antecipacao':
      return 'Pode ser antecipação'
  }
}

export function textoDaSeveridade(severidade: Esquemas['Severidade']): string {
  switch (severidade) {
    case 'falta_de_verdade':
      return 'Falta de verdade'
    case 'para_conferir':
      return 'Para conferir'
  }
}

/** De onde vem a pendência: os recebíveis do grupo ou, no item de crédito, o lançamento. */
export function origem(item: Item): string {
  const [primeiro, ...resto] = item.recebiveis
  if (primeiro) {
    const mais = resto.length ? ` e mais ${resto.length}` : ''
    return `${primeiro.adquirente} · NSU ${primeiro.nsu} · parcela ${primeiro.parcela}/${primeiro.parcelas}${mais}`
  }
  return item.creditos.map((c) => `crédito de ${dia.format(new Date(c.lancado_em))} · ${c.descricao}`).join(', ')
}
