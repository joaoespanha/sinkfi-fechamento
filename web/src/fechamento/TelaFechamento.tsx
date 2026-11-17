import { useEffect, useState } from 'react'
import {
  type Fechamento,
  type Item,
  emReais,
  linhaDoResumo,
  origem,
  paraConferir,
  textoDaSeveridade,
  textoDoMotivo,
} from './textos'

type Estado =
  | { tipo: 'carregando' }
  | { tipo: 'sem_rodada' }
  | { tipo: 'erro' }
  | { tipo: 'pronto'; fechamento: Fechamento }

type Pendencia = Item & {
  severidade: NonNullable<Item['severidade']>
  motivo: NonNullable<Item['motivo']>
  pendencia_centavos: number
}

function pendencias(itens: Item[]): Pendencia[] {
  return itens
    .filter((i): i is Pendencia => i.severidade != null && i.motivo != null && i.pendencia_centavos != null)
    // Faltas de verdade primeiro; dentro de cada severidade, o maior valor primeiro.
    .sort(
      (a, b) =>
        Number(a.severidade !== 'falta_de_verdade') - Number(b.severidade !== 'falta_de_verdade') ||
        b.pendencia_centavos - a.pendencia_centavos,
    )
}

export function TelaFechamento({ clienteId }: { clienteId: string }) {
  const [estado, setEstado] = useState<Estado>({ tipo: 'carregando' })

  useEffect(() => {
    const controle = new AbortController()
    fetch(`/api/clientes/${encodeURIComponent(clienteId)}/fechamento`, { signal: controle.signal })
      .then(async (resposta) => {
        if (resposta.status === 404) return setEstado({ tipo: 'sem_rodada' })
        if (!resposta.ok) return setEstado({ tipo: 'erro' })
        setEstado({ tipo: 'pronto', fechamento: (await resposta.json()) as Fechamento })
      })
      .catch((erro: unknown) => {
        if (!controle.signal.aborted) {
          console.error(erro)
          setEstado({ tipo: 'erro' })
        }
      })
    return () => controle.abort()
  }, [clienteId])

  switch (estado.tipo) {
    case 'carregando':
      return <p aria-busy="true">Carregando o fechamento…</p>
    case 'sem_rodada':
      return <p>Ainda não há fechamento calculado.</p>
    case 'erro':
      return <p role="alert">Não foi possível carregar o fechamento. Tente de novo em instantes.</p>
    case 'pronto':
      return <Detalhe fechamento={estado.fechamento} />
  }
}

function Detalhe({ fechamento }: { fechamento: Fechamento }) {
  const { resumo, rodada } = fechamento
  const conferir = paraConferir(resumo)
  const lista = pendencias(fechamento.itens)
  const corte = new Date(rodada.corte).toLocaleString('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Sao_Paulo',
  })

  return (
    <>
      <header className="resumo" data-recomendacao={resumo.recomendacao}>
        <p className="resumo-linha">{linhaDoResumo(resumo)}</p>
        {conferir && <p className="resumo-conferir">{conferir}</p>}
        <p className="resumo-corte">Fechamento com corte em {corte}</p>
      </header>

      {lista.length > 0 && (
        <div className="tabela" role="region" aria-labelledby="pendencias-titulo" tabIndex={0}>
          <table>
            <caption id="pendencias-titulo">Pendências</caption>
            <thead>
              <tr>
                <th scope="col">Motivo</th>
                <th scope="col">Severidade</th>
                <th scope="col">Origem</th>
                <th scope="col" className="valor">
                  Valor
                </th>
              </tr>
            </thead>
            <tbody>
              {lista.map((p, i) => (
                <tr key={i} data-severidade={p.severidade}>
                  <th scope="row">{textoDoMotivo(p.motivo)}</th>
                  <td>{textoDaSeveridade(p.severidade)}</td>
                  <td>{origem(p)}</td>
                  <td className="valor">{emReais(p.pendencia_centavos)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
