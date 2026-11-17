import type { components } from '../api'

type Esquemas = components['schemas']
export type Fechamento = Esquemas['FechamentoResposta']
export type Item = Esquemas['ItemLido']
export type Termino = Esquemas['TerminoLido']
export type Semana = Esquemas['SemanaLida']
type Resumo = Esquemas['ResumoLido']
type Recebivel = Esquemas['Recebivel']
type Lancamento = Esquemas['Lancamento']

const dia = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', timeZone: 'America/Sao_Paulo' })
const diaEHora = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'short',
  timeZone: 'America/Sao_Paulo',
})
const reais = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export function emReais(centavos: number): string {
  return reais.format(centavos / 100)
}

export function quando(iso: string): string {
  return diaEHora.format(new Date(iso))
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

/** "2026-11-10" vira "10/11". A semana já é uma data do fuso do cliente: não passa por `Date`. */
export function diaDaSemana(semana: string): string {
  const [, mes, dia] = semana.split('-')
  return `${dia}/${mes}`
}

export function rotuloDaSemana(s: Semana): string {
  const marcas = [s.atual && 'atual', !s.tem_rodada && 'não calculado'].filter(Boolean)
  return marcas.length ? `${diaDaSemana(s.semana)} (${marcas.join(', ')})` : diaDaSemana(s.semana)
}

/** O aviso de fechamento anterior com pendência e sem "Terminei" (ADR 0007). */
export function textoDoAviso(s: Semana): string {
  const faltas = s.itens_falta_de_verdade ?? 0
  const conferir = s.itens_para_conferir ?? 0
  const partes = [
    faltas > 0 && (faltas === 1 ? '1 falta de verdade' : `${faltas} faltas de verdade`),
    conferir > 0 && `${conferir} para conferir`,
  ].filter(Boolean)
  return `Você ainda não terminou o fechamento de ${diaDaSemana(s.semana)}: ${partes.join(', ')}.`
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

/** Por que a regra marcou o grupo (GLOSSARY). O `switch` é exaustivo: um motivo novo não compila. */
export function explicacaoDoMotivo(motivo: Esquemas['Motivo']): string {
  switch (motivo) {
    case 'nao_caiu':
      return 'O recebível tinha liquidação prevista até o fechamento e nenhum crédito dele entrou na conta até o corte.'
    case 'caiu_em_parte':
      return 'Entrou na conta menos do que o esperado para este recebível. A diferença é o valor da pendência.'
    case 'grupo_nao_fecha':
      return 'Um crédito serve para mais de um recebível, então eles ficam juntos. O que caiu não cobre o grupo, e não dá para saber qual recebível ficou sem pagar.'
    case 'chargeback':
      return 'Um lançamento de saída desfez um crédito já casado: o dinheiro deste recebível saiu da conta.'
    case 'venda_cancelada':
      return 'A venda foi desfeita, mas caiu dinheiro por ela. Esse dinheiro não é seu e deve voltar para a adquirente.'
    case 'entrada_sem_recebivel':
      return 'Entrou um crédito que não casa com nenhum recebível. Não muda o fechamento, mas vale conferir de onde veio.'
    case 'pode_ser_antecipacao':
      return 'Entrou um crédito ligado a uma venda cujo recebível não vence neste fechamento. Pode ser uma antecipação.'
  }
}

/** Os CSVs trazem a adquirente em minúsculas (`stone`); na tela vai com inicial maiúscula. */
export function nomeDaAdquirente(adquirente: string): string {
  return adquirente.charAt(0).toLocaleUpperCase('pt-BR') + adquirente.slice(1)
}

export function linhaDoRecebivel(r: Recebivel): string {
  return `${nomeDaAdquirente(r.adquirente)} · NSU ${r.nsu} · parcela ${r.parcela}/${r.parcelas} · previsto para ${dia.format(new Date(`${r.liquidacao_prevista}T12:00:00`))}`
}

export function linhaDoCredito(c: Lancamento): string {
  return `${dia.format(new Date(c.lancado_em))} · ${c.descricao}`
}

/** De onde vem a pendência: os recebíveis do grupo ou, no item de crédito, o lançamento. */
export function origem(item: Item): string {
  const [primeiro, ...resto] = item.recebiveis
  if (primeiro) {
    const mais = resto.length ? ` e mais ${resto.length}` : ''
    return `${nomeDaAdquirente(primeiro.adquirente)} · NSU ${primeiro.nsu} · parcela ${primeiro.parcela}/${primeiro.parcelas}${mais}`
  }
  return item.creditos.map((c) => `crédito de ${dia.format(new Date(c.lancado_em))} · ${c.descricao}`).join(', ')
}

/** O campo do limite em reais, como a lojista digita ("2.000" ou "2000,50"). Vazio desliga a trava. */
export function centavosDoCampo(texto: string): number | null | 'invalido' {
  const limpo = texto.replace(/R\$|\s/g, '')
  if (limpo === '') return null
  if (!/^(\d{1,3}(\.\d{3})+|\d+)(,\d{1,2})?$/.test(limpo)) return 'invalido'
  return Math.round(Number(limpo.replace(/\./g, '').replace(',', '.')) * 100)
}

export function campoDosCentavos(centavos: number | null): string {
  return centavos === null ? '' : (centavos / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2 })
}
