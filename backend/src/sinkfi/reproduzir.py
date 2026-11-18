"""Reproduzir uma rodada gravada (Debugar): a entrada ainda é a mesma, a versão é a de hoje e a regra decide igual?

Uso, no container da api: `python -m sinkfi.reproduzir <cliente_id> <rodada_id>`.
Só lê: não grava rodada nem faz commit.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from fechamento import VERSAO_DA_REGRA, Recebivel, fechar
from sinkfi.banco import engine, repositorios
from sinkfi.rodadas import hash_da_rodada, itens_do_fechamento
from sinkfi.tipos import Entrada, ItemRodada, Rodada


@dataclass(frozen=True)
class Reproducao:
    rodada: Rodada
    # O corte no fuso do cliente, como a regra recebeu.
    corte: datetime
    versao_de_hoje: str
    # O hash da entrada de hoje, com o corte e a versão da rodada, bate com o gravado.
    mesma_entrada: bool
    # Recebíveis e lançamentos da cópia gravada que mudaram ou sumiram do banco. Só quando a entrada mudou;
    # vazio com entrada mudada quer dizer que entrou dado novo, que a cópia não tinha.
    mudaram: list[str]
    # Os itens em que a regra de hoje decide diferente da gravada. Só quando a entrada é a mesma.
    so_na_gravada: list[ItemRodada]
    so_na_de_hoje: list[ItemRodada]

    @property
    def mesma_versao(self) -> bool:
        return self.rodada.versao_regra == self.versao_de_hoje


def reproduzir(sessao: Session, cliente_id: str, rodada_id: int) -> Reproducao | None:
    """None quando a rodada não existe ou é de outro cliente."""
    rodada = repositorios.rodada_do_cliente(sessao, cliente_id, rodada_id)
    if rodada is None:
        return None
    # O banco devolve o corte em UTC, mas o hash foi feito com ele no fuso do cliente.
    fuso = ZoneInfo(repositorios.config_do_cliente(sessao, cliente_id).fuso)
    corte = rodada.corte.astimezone(fuso)
    entrada = repositorios.entrada_do_cliente(sessao, cliente_id)
    gravados = repositorios.itens_da_rodada(sessao, rodada.id)

    if hash_da_rodada(entrada, corte, rodada.versao_regra) != rodada.hash_entrada:
        return Reproducao(rodada, corte, VERSAO_DA_REGRA, False, _mudaram(entrada, gravados), [], [])

    de_hoje = itens_do_fechamento(fechar(entrada.recebiveis, entrada.lancamentos, entrada.lojas, corte))
    return Reproducao(rodada, corte, VERSAO_DA_REGRA, True, [], _sem(gravados, de_hoje), _sem(de_hoje, gravados))


def _mudaram(entrada: Entrada, gravados: list[ItemRodada]) -> list[str]:
    # O recebível é nomeado com a adquirente: o id sozinho pode ser de duas (ADR 0009).
    atuais = {_nome(r): r for r in entrada.recebiveis} | {l.id: l for l in entrada.lancamentos}
    copias = {_nome(r): r for i in gravados for r in i.recebiveis} | {c.id: c for i in gravados for c in i.creditos}
    return sorted(nome for nome, copia in copias.items() if atuais.get(nome) != copia)


def _nome(r: Recebivel) -> str:
    return f"{r.id} ({r.adquirente})"


def _sem(itens: list[ItemRodada], outros: list[ItemRodada]) -> list[ItemRodada]:
    """Os itens que não estão em `outros`, contando repetidos."""
    restantes = list(outros)
    sobra = []
    for item in itens:
        if item in restantes:
            restantes.remove(item)
        else:
            sobra.append(item)
    return sobra


def relatorio(r: Reproducao) -> str:
    rodada = r.rodada
    linhas = [
        f"Rodada {rodada.id} de {rodada.cliente_id}: fechamento de {rodada.data_fechamento}, "
        f"corte {r.corte.isoformat()}, criada em {rodada.criada_em.isoformat()}.",
        f"Versão da regra: {rodada.versao_regra}"
        + ("." if r.mesma_versao else f", e a de hoje é {r.versao_de_hoje}: a regra mudou desde então."),
    ]
    if not r.mesma_entrada:
        linhas.append("Entrada: mudou desde a rodada, então não dá para rodar a regra de novo sobre ela.")
        linhas.append(
            f"Da cópia gravada, mudaram ou sumiram: {', '.join(r.mudaram)}."
            if r.mudaram
            else "Nada da cópia gravada mudou: entrou dado novo depois da rodada."
        )
        return "\n".join(linhas)
    linhas.append("Entrada: a mesma de hoje.")
    if not r.so_na_gravada and not r.so_na_de_hoje:
        linhas.append("Decisão: a regra de hoje decide igual, item a item.")
        return "\n".join(linhas)
    linhas.append("Decisão: a regra de hoje decide diferente.")
    linhas += [f"  só na gravada: {_item(i)}" for i in r.so_na_gravada]
    linhas += [f"  só na de hoje: {_item(i)}" for i in r.so_na_de_hoje]
    return "\n".join(linhas)


def _item(i: ItemRodada) -> str:
    motivo = i.motivo.value if i.motivo else "casou"
    recebiveis = ",".join(_nome(r) for r in i.recebiveis) or "-"
    creditos = ",".join(c.id for c in i.creditos) or "-"
    pendencia = f", pendência {i.pendencia_centavos} centavos" if i.pendencia_centavos is not None else ""
    return f"{motivo} (recebíveis {recebiveis}; créditos {creditos}{pendencia})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sinkfi.reproduzir", description=__doc__.splitlines()[0])
    parser.add_argument("cliente_id")
    parser.add_argument("rodada_id", type=int)
    args = parser.parse_args(argv)
    with Session(engine()) as sessao:
        r = reproduzir(sessao, args.cliente_id, args.rodada_id)
        if r is None:
            print(f"Rodada {args.rodada_id} não encontrada para {args.cliente_id}.")
            return 1
        print(relatorio(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
