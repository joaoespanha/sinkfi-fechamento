// A busca do suporte por um cliente (ADR 0010): o que vai à api e como cada resultado aparece.
import { describe, expect, it } from 'vitest'
import { avisoDaBusca, type ClienteEncontrado, descreverLojas, termoBuscavel } from './busca'

describe('termoBuscavel', () => {
  it('tira os espaços e devolve o termo com 3 caracteres ou mais', () => {
    expect(termoBuscavel('  mar  ')).toBe('mar')
  })

  it('devolve null para termo curto, que a api recusaria com 422', () => {
    expect(termoBuscavel('')).toBeNull()
    expect(termoBuscavel(' ma ')).toBeNull()
  })
})

describe('descreverLojas', () => {
  const marina: ClienteEncontrado = {
    id: 'cli_marina',
    nome: 'Marina',
    lojas: [
      { nome: 'Loja Centro', documento: '10493827000160' },
      { nome: 'Loja Savassi', documento: '10493827000160' },
    ],
  }

  it('lista as lojas e mostra o CNPJ repetido uma vez só, com pontuação', () => {
    expect(descreverLojas(marina)).toBe('Loja Centro, Loja Savassi · CNPJ 10.493.827/0001-60')
  })

  it('mostra cada CNPJ diferente', () => {
    const rede = { ...marina, lojas: [...marina.lojas, { nome: 'Loja Pampulha', documento: '11222333000181' }] }
    expect(descreverLojas(rede)).toBe(
      'Loja Centro, Loja Savassi, Loja Pampulha · CNPJ 10.493.827/0001-60, 11.222.333/0001-81',
    )
  })

  it('diz quando o cliente ainda não tem loja', () => {
    expect(descreverLojas({ ...marina, lojas: [] })).toBe('Sem lojas cadastradas')
  })

  it('mostra como veio o documento que não tem 14 dígitos', () => {
    expect(descreverLojas({ ...marina, lojas: [{ nome: 'Loja X', documento: '123' }] })).toBe('Loja X · CNPJ 123')
  })
})

describe('avisoDaBusca', () => {
  it('diz que nada foi encontrado', () => {
    expect(avisoDaBusca(0)).toBe('Nenhum cliente encontrado.')
  })

  it('não diz nada quando a lista veio inteira', () => {
    expect(avisoDaBusca(1)).toBeNull()
    expect(avisoDaBusca(9)).toBeNull()
  })

  it('pede um termo mais específico quando a lista veio cheia, porque pode ter cortado clientes', () => {
    expect(avisoDaBusca(10)).toBe('Mostrando os 10 primeiros. Use um termo mais específico.')
  })
})
