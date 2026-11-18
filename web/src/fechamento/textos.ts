import type { components } from '../api'

type Esquemas = components['schemas']
export type Fechamento = Esquemas['FechamentoResposta']
export type Item = Esquemas['ItemLido']
export type Conferencia = Esquemas['ConferenciaLida']
export type Semana = Esquemas['SemanaLida']
export type Atualizacao = Esquemas['AtualizacaoLida']
export type Resolucao = Esquemas['ResolucaoLida']
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

const diaCurtoEHora = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'America/Sao_Paulo',
})
const hora = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' })

/** "às 21:00" no mesmo dia de `referencia`; "19/11 às 03:00" em outro dia ou sem referência. */
function asHoras(iso: string, referencia: string | null): string {
  const d = new Date(iso)
  const mesmoDia = referencia !== null && dia.format(d) === dia.format(new Date(referencia))
  return mesmoDia ? `às ${hora.format(d)}` : `${dia.format(d)} às ${hora.format(d)}`
}

/**
 * A linha de atualização do resumo (ADR 0011, GLOSSARY: Atualização). O dia da próxima é comparado com o da
 * última, não com o relógio da tela: o texto depende só do que a api devolveu.
 */
export function linhaDaAtualizacao(a: Atualizacao): string {
  const proxima = asHoras(a.proxima_prevista_em, a.ultima_em)
  if (a.ultima_em === null) {
    return `Ainda sem atualização · primeira prevista ${proxima}`
  }
  const ultima = diaCurtoEHora.format(new Date(a.ultima_em))
  if (a.atrasada && a.primeira_perdida_em) {
    const perdida = asHoras(a.primeira_perdida_em, null)
    return `Dados de ${ultima} · a atualização prevista para ${perdida} não aconteceu · próxima prevista ${proxima}`
  }
  return `Dados atualizados em ${ultima} · próxima atualização prevista ${proxima}`
}

function itens(n: number): string {
  return n === 1 ? '1 item' : `${n} itens`
}

/**
 * A linha do resumo (GLOSSARY: Resumo). O `switch` é exaustivo: uma recomendação nova não compila.
 * Sem "seu": a lojista e o suporte leem a mesma linha.
 */
export function linhaDoResumo(resumo: Resumo): string {
  const falta = emReais(resumo.falta_de_verdade_centavos)
  const limite = resumo.limite_trava_centavos
  switch (resumo.recomendacao) {
    case 'pode_fechar':
      // Com a trava ligada, pode fechar mesmo com faltas, se a soma ficar dentro do limite.
      return resumo.itens_falta_de_verdade === 0 || limite === null
        ? 'Pode fechar'
        : `Pode fechar: faltam ${falta}, dentro do limite de ${emReais(limite)}`
    case 'faltam':
      return `Faltam ${falta} em ${itens(resumo.itens_falta_de_verdade)}`
    case 'nao_feche':
      // `nao_feche` só existe com a trava ligada; o `?? 0` é só para o tipo.
      return `Não feche: faltam ${falta}, acima do limite de ${emReais(limite ?? 0)}`
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

/** O aviso de fechamento anterior com pendência e sem conferência (ADR 0007). Sem "você": o suporte também lê. */
export function textoDoAviso(s: Semana): string {
  const faltas = s.itens_falta_de_verdade ?? 0
  const conferir = s.itens_para_conferir ?? 0
  const partes = [
    faltas > 0 && (faltas === 1 ? '1 falta de verdade' : `${faltas} faltas de verdade`),
    conferir > 0 && `${conferir} para conferir`,
  ].filter(Boolean)
  return `O fechamento de ${diaDaSemana(s.semana)} ainda não foi conferido: ${partes.join(', ')}.`
}

// A faixa do suporte: a tela é a da lojista, e a faixa diz isso e mostra a conferência vista de fora.

export function fraseDaFaixa(nomeDoCliente: string): string {
  return `Você está vendo o fechamento como ${nomeDoCliente} vê.`
}

/** A conferência mais recente, para o suporte: quem (o e-mail), quando e em qual rodada. */
export function fraseDaConferencia(conferencia: Conferencia | null, rodadaId: number): string {
  if (!conferencia) return 'Ninguém conferiu este fechamento ainda.'
  const quem = `${conferencia.quem} conferiu em ${quando(conferencia.em)}`
  return conferencia.rodada_id === rodadaId
    ? `${quem}, nesta rodada.`
    : `${quem}, na rodada ${conferencia.rodada_id}. Esta é a rodada ${rodadaId}.`
}

// A conferência da lojista (ADR 0012): um registro que não trava nada.

const CAMPOS_DO_RESUMO = [
  'recomendacao',
  'falta_de_verdade_centavos',
  'itens_falta_de_verdade',
  'itens_para_conferir',
  'limite_trava_centavos',
] as const satisfies readonly (keyof Resumo)[]

/**
 * Se o botão aparece. Some quando a conferência mais recente já vale para o que a tela mostra: a mesma
 * rodada e o mesmo resumo. O limite é lido na hora (ADR 0006), então o resumo muda sem rodada nova.
 */
export function podeConferir(conferencia: Conferencia | null, rodadaId: number, resumo: Resumo): boolean {
  if (!conferencia || conferencia.rodada_id !== rodadaId) return true
  return CAMPOS_DO_RESUMO.some((campo) => conferencia.resumo[campo] !== resumo[campo])
}

/** A linha do aviso: a do resumo e a contagem para conferir, que resolver e desfazer mudam (ADR 0014). */
function linhaDoAviso(resumo: Resumo): string {
  const conferir = paraConferir(resumo)
  return conferir ? `${linhaDoResumo(resumo)} · ${conferir}` : linhaDoResumo(resumo)
}

/**
 * O que o aviso da conferência que já não vale mostra: o antes e o agora, ou, quando as linhas seriam iguais,
 * por que ela deixou de valer. Rodada nova com o mesmo resumo acontece quando a versão da regra muda.
 */
export function mudancaDaConferencia(
  conferencia: Conferencia,
  rodadaId: number,
  resumo: Resumo,
): { antes: string; agora: string } | { mesmoResumo: string } {
  const antes = linhaDoAviso(conferencia.resumo)
  const agora = linhaDoAviso(resumo)
  if (antes !== agora) return { antes, agora }
  const motivo = conferencia.rodada_id !== rodadaId ? 'O fechamento foi recalculado' : 'O limite da trava mudou'
  return { mesmoResumo: `${motivo}, e o resumo continua o mesmo: ${agora}.` }
}

/** O estado no lugar do botão. */
export function fraseDoConferido(conferencia: Conferencia): string {
  return `Conferido por ${conferencia.quem} em ${quando(conferencia.em)}`
}

/** O que a confirmação diz que não muda: conferir não resolve os itens para conferir nem trava nada. */
export function avisoDaConfirmacao(resumo: Resumo): string {
  const n = resumo.itens_para_conferir
  if (n === 0) return 'Nada trava.'
  if (n === 1) return 'O item para conferir continua na lista. Nada trava.'
  return `Os ${n} itens para conferir continuam na lista. Nada trava.`
}

// A resolução da lojista (ADR 0014): tira uma pendência para conferir da lista, com uma nota.

/** O mesmo limite do backend (`ResolucaoEntrada`). */
export const NOTA_MAXIMA = 200

/**
 * Se o botão aparece. Só o item de crédito para conferir: a resolução é presa ao lançamento, e a falta de
 * verdade é dinheiro que não entrou, então não se resolve.
 */
export function podeResolver(item: Item): boolean {
  return (
    item.severidade === 'para_conferir' &&
    item.recebiveis.length === 0 &&
    item.creditos.length === 1 &&
    item.resolucao == null
  )
}

export function fraseDaResolucao(r: Resolucao): string {
  return `Resolvida por ${r.quem} em ${quando(r.em)}`
}

export const PEDIDO_ENVIADO = 'Pedido enviado. Se a entrada mudou, a rodada nova aparece em instantes.'

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
    case 'caiu_a_mais':
      return 'Caiu a mais'
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
    case 'caiu_a_mais':
      return 'Entrou na conta mais do que o esperado para este recebível. O que passa do esperado é o valor da pendência: esse dinheiro não é seu, e a adquirente pode cobrar de volta.'
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

// Dia de cada item (#26)

const nomeDoDiaFmt = new Intl.DateTimeFormat('pt-BR', {
  weekday: 'short',
  day: '2-digit',
  month: '2-digit',
  timeZone: 'UTC',
})
const dataNoFuso = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' })

/** A casa da faixa para os itens com `dia` null (#26). */
export const ANTES = 'antes'

/** Os 7 dias da semana: do dia seguinte ao corte anterior até o dia do corte. Datas ISO, sem fuso. */
export function diasDaSemana(semana: string): string[] {
  const corte = new Date(`${semana}T00:00:00Z`)
  return Array.from({ length: 7 }, (_, k) =>
    new Date(corte.getTime() - (6 - k) * 86_400_000).toISOString().slice(0, 10),
  )
}

/** "2026-11-04" vira "qua., 04/11". */
export function nomeDoDia(dia: string): string {
  return dia === ANTES ? 'Antes desta semana' : nomeDoDiaFmt.format(new Date(`${dia}T12:00:00Z`))
}

/** A data ISO de um instante no fuso do cliente. */
function diaNoFuso(iso: string): string {
  return dataNoFuso.format(new Date(iso))
}

export function casaDoItem(item: Item): string {
  return item.dia ?? ANTES
}

/**
 * O id do endereço do item: o do primeiro recebível, ou o do crédito. É do domínio, então sobrevive a um reprocessamento.
 */
export function chaveDoItem(item: Item): string {
  const primeiro = item.recebiveis[0]
  return primeiro ? chaveDoRecebivel(primeiro) : (item.creditos[0]?.id ?? '')
}

/** O item de uma chave: o grupo que tem o recebível, ou o item de crédito com aquele crédito. */
export function acharItem(itens: Item[], chave: string): Item | undefined {
  return (
    itens.find((i) => i.recebiveis.some((r) => chaveDoRecebivel(r) === chave)) ??
    itens.find((i) => i.recebiveis.length === 0 && i.creditos.some((c) => c.id === chave))
  )
}

/** O id do recebível só é único dentro da adquirente, então a chave leva as duas coisas (ADR 0009). */
export function chaveDoRecebivel(r: Item['recebiveis'][number]): string {
  return `${r.adquirente}:${r.id}`
}

/** O valor que a lista mostra: a pendência, ou o esperado do grupo, ou o que caiu no item de crédito. */
export function valorDoItem(item: Item): number {
  return item.pendencia_centavos ?? item.esperado_centavos ?? item.creditos.reduce((s, c) => s + c.valor_centavos, 0)
}

/** A venda aparece no dia previsto; diz quando o dinheiro caiu em outro dia ou ficou para depois do corte. */
export function notaDoDia(item: Item): string | null {
  if (item.recebiveis.length === 0) return null
  if (item.proximo_fechamento_centavos) return 'entra no próximo fechamento'
  const outro = item.creditos.map((c) => diaNoFuso(c.lancado_em)).find((d) => d !== item.dia)
  return outro ? `caiu em ${diaDaSemana(outro)}` : null
}

/** O NSU aparece inteiro na descrição, com a mesma fronteira da regra: "STN-1" não está em "STN-12". */
function citaNsu(nsu: string, descricao: string): boolean {
  const escapado = nsu.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return new RegExp(`(?<![0-9A-Za-z])${escapado}(?![0-9A-Za-z])`).test(descricao)
}

/**
 * Por qual chave o item casou (GLOSSARY: Chave forte, Chave fraca). A chave fraca só vale para crédito
 * que não cita o NSU de nenhum recebível; então NSU na descrição quer dizer chave forte.
 */
export function textoDaChave(item: Item): string {
  const forte = item.creditos.some((c) => item.recebiveis.some((r) => citaNsu(r.nsu, c.descricao)))
  return forte
    ? 'Casou pela chave forte: o NSU da venda está na descrição do crédito.'
    : 'Casou pela chave fraca: mesma adquirente e mesmo valor líquido, dentro da janela.'
}

/** O que a lojista faz com a pendência. O `switch` é exaustivo: um motivo novo não compila. */
export function oQueFazer(motivo: Esquemas['Motivo'], item: Item): string {
  const r = item.recebiveis[0]
  const c = item.creditos[0]
  const adquirente = r ? nomeDaAdquirente(r.adquirente) : 'adquirente'
  const valor = emReais(item.pendencia_centavos ?? 0)
  const credito = c ? `crédito de ${emReais(c.valor_centavos)} em ${diaDaSemana(diaNoFuso(c.lancado_em))}` : 'crédito'
  switch (motivo) {
    case 'nao_caiu':
      return `Confira no portal da ${adquirente} se a venda NSU ${r?.nsu} foi liquidada, e em qual conta. Se não foi, abra um chamado com o NSU e a data prevista, ${r ? diaDaSemana(r.liquidacao_prevista) : ''}.`
    case 'caiu_em_parte':
      return `O esperado já desconta a taxa e a antecipação da venda, então a diferença de ${valor} não é taxa prevista. Compare com o extrato da ${adquirente} e, se não tiver explicação, abra um chamado com o NSU ${r?.nsu} e a diferença.`
    case 'grupo_nao_fecha':
      return `Peça à ${adquirente} o detalhamento do ${credito}. Com ele dá para saber qual venda ficou sem pagar.`
    case 'chargeback':
      return `Veja no portal da ${adquirente} o motivo da contestação da venda NSU ${r?.nsu}. Se for contestar, junte o comprovante de entrega dentro do prazo da ${adquirente}.`
    case 'venda_cancelada':
      return `Confirme com a adquirente se os ${valor} vão ser descontados de um repasse futuro ou se você precisa devolver. O crédito é "${c?.descricao}".`
    case 'entrada_sem_recebivel':
      return `Confira quem mandou o ${credito} ("${c?.descricao}"). Se for uma venda, ela pode estar faltando no arquivo da adquirente.`
    case 'pode_ser_antecipacao':
      return `Confira se você pediu antecipação da venda ligada ao ${credito} ("${c?.descricao}"). Se pediu, não há nada a fazer agora. Se não pediu, pergunte à adquirente.`
    case 'caiu_a_mais':
      return `Confira no extrato da ${adquirente} se a venda NSU ${r?.nsu} foi paga duas vezes ou com valor maior. Confirme com a ${adquirente} se os ${valor} a mais vão ser descontados de um repasse futuro ou se você precisa devolver.`
  }
}

// Interface (#32): gráficos, filtros e o "?" ao lado dos termos

const porcento = new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 0 })

/** A fração de um total, já formatada ("66%"). Total zero vira "0%". */
export function emPorcento(parte: number, todo: number): string {
  return porcento.format(todo > 0 ? parte / todo : 0)
}

/** O "?" ao lado de cada termo: a definição do GLOSSARY.md, com as palavras da lojista. */
export const TERMOS = {
  corte: {
    nome: 'Corte',
    texto: 'O momento que separa um fechamento do seguinte. O seu é segunda às 18:00, horário de São Paulo. O que cai depois entra no fechamento seguinte.',
  },
  esperado: {
    nome: 'Esperado',
    texto: 'A soma dos recebíveis com liquidação prevista até o dia do fechamento, desde o início, não só desta semana. Esperado = Caiu + Não caiu + Próximo fechamento.',
  },
  caiu: {
    nome: 'Caiu',
    texto: 'A parte do esperado confirmada na conta até o corte e não desfeita por chargeback.',
  },
  naoCaiu: {
    nome: 'Não caiu',
    texto: 'A parte do esperado que não está na conta: não foi depositada, foi depositada em parte ou saiu por chargeback.',
  },
  proximo: {
    nome: 'Próximo fechamento',
    texto: 'A parte do esperado cujo crédito casou, mas caiu depois do corte ou ainda não foi confirmado. Não é pendência: entra no fechamento seguinte.',
  },
  falta: {
    nome: 'Falta de verdade',
    texto: 'Dinheiro que muda o fechamento: não entrou, ou entrou e não é seu. É o que pesa na recomendação.',
  },
  conferir: {
    nome: 'Para conferir',
    texto: 'Vale olhar, mas não muda o fechamento, como um crédito que não casa com nenhuma venda.',
  },
  trava: {
    nome: 'Trava',
    texto: 'O limite que você define sobre a soma das faltas de verdade. Acima dele, o resumo recomenda não fechar. Nunca impede de fechar.',
  },
} as const

export type Termo = keyof typeof TERMOS

/** As partes do esperado, na ordem da barra e da legenda. */
export const PARTES = [
  { chave: 'caiu', termo: 'caiu' },
  { chave: 'nao-caiu', termo: 'naoCaiu' },
  { chave: 'proximo', termo: 'proximo' },
] as const

export const LEGENDA_DA_FAIXA =
  'Cada dia mostra quanto caiu; a barra é o esperado do dia, e a parte cheia, o que caiu. Passe o mouse ou o foco num dia para ver o detalhe; clique para filtrar a lista.'

export const ABAS = [
  { valor: 'todas', nome: 'Todas' },
  { valor: 'falta_de_verdade', nome: 'Faltas de verdade' },
  { valor: 'para_conferir', nome: 'Para conferir' },
] as const

export const ORDENS = [
  { valor: 'severidade', nome: 'Faltas primeiro' },
  { valor: 'valor', nome: 'Maior valor' },
  { valor: 'dia', nome: 'Dia' },
] as const

export const SEM_PENDENCIA_NO_FILTRO = 'Nenhuma pendência com esses filtros.'

/** As marcas do cartão do dia: "1 falta", "3 faltas", "2 conferir". */
export function marcaDeFaltas(n: number): string {
  return n === 1 ? '1 falta' : `${n} faltas`
}

export function marcaDeConferir(n: number): string {
  return `${n} conferir`
}

type DiaDaFaixa = {
  casa: string
  vazio: boolean
  esperado: number
  caiu: number
  naoCaiu: number
  proximo: number
  faltas: number
  conferir: number
  certos: number
}

/** A dica de um dia da faixa, que também é o nome do link para o leitor de tela. */
export function dicaDoDia(d: DiaDaFaixa): string {
  if (d.vazio) return `${nomeDoDia(d.casa)}: nada previsto nem caído`
  const valores = [
    `esperado ${emReais(d.esperado)}`,
    `caiu ${emReais(d.caiu)}`,
    `não caiu ${emReais(d.naoCaiu)}`,
    d.proximo > 0 && `próximo fechamento ${emReais(d.proximo)}`,
  ].filter(Boolean)
  const marcas = [
    d.faltas > 0 && (d.faltas === 1 ? '1 falta de verdade' : `${d.faltas} faltas de verdade`),
    d.conferir > 0 && `${d.conferir} para conferir`,
    d.certos > 0 && (d.certos === 1 ? '1 casou certo' : `${d.certos} casaram certo`),
  ].filter(Boolean)
  return `${nomeDoDia(d.casa)}: ${valores.join(', ')}.${marcas.length ? ` ${marcas.join(', ')}.` : ''}`
}
