"""Gera os lotes de teste em dados-teste/lote1 e dados-teste/lote2.

Cada lote é a pasta dados/ inteira (a base do repositório mais as linhas novas), pronta para copiar
por cima de dados/. O lote 2 contém o lote 1: a ingestão atualiza pelo id e não apaga.

A base vem de `git show HEAD:dados/...`, não do disco: com um lote já copiado por cima de dados/, ler
o disco repetiria as linhas novas.

Semanas (corte terça 18:00 de Brasília): 03/11 (28/10 a 03/11), 10/11 (a base) e 17/11 (11/11 a 17/11).
"""

import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

STONE = "STONE PAGAMENTOS,16501555000100"
PAG = "PAGSEGURO,08561701000100"

# ---------- Lote 1: a semana de 03/11 e a semana de 17/11 chegando ----------

REC_LOTE1 = [
    # Semana 03/11
    "rec_3101,loja_centro,stone,card,2026-10-29,2026-10-30,100000,1500,0,98500,STN-3101,1,1,open",  # casa pelo NSU
    "rec_3102,loja_savassi,pagseguro,card,2026-10-30,2026-11-02,62500,1250,0,61250,PAG-3102,1,1,open",  # casa sem NSU (chave fraca)
    "rec_3103,loja_centro,stone,card,2026-10-31,2026-11-03,233500,3500,0,230000,STN-3103,1,1,open",  # não caiu (chega no lote 2)
    # Semana 17/11
    "rec_1701,loja_centro,stone,card,2026-11-12,2026-11-13,199000,3000,0,196000,STN-1701,1,1,open",  # A: casa pelo NSU (+ linha repetida no extrato)
    "rec_1702,loja_savassi,pagseguro,card,2026-11-11,2026-11-12,75000,1520,0,73480,PAG-1702,1,1,open",  # B: chave fraca
    "rec_1703,loja_centro,stone,card,2026-11-14,2026-11-16,317600,4700,0,312900,STN-1703,1,1,open",  # C: não caiu
    "rec_1704,loja_savassi,pagseguro,card,2026-11-13,2026-11-16,255000,5000,0,250000,PAG-1704,1,1,open",  # D: caiu em parte
    "rec_1705,loja_centro,stone,card,2026-11-12,2026-11-14,86300,1300,0,85000,STN-1705,1,1,open",  # E: caiu a mais
    "rec_1706,loja_centro,stone,card,2026-11-15,2026-11-17,426300,6300,0,420000,STN-1706,1,1,open",  # F: pending -> próximo
    "rec_1707,loja_savassi,pagseguro,pix,2026-11-15,2026-11-15,35000,0,0,35000,PIX-1707,1,1,open",  # G: Pix casa
    "rec_1708,loja_savassi,pagseguro,card,2026-11-15,2026-11-17,55400,1080,0,54320,PAG-1708,1,1,open",  # H: caiu depois do corte
    "rec_1709,loja_savassi,pagseguro,card,2026-11-10,2026-11-12,130000,2000,0,128000,PAG-1709,1,1,open",  # I: chargeback no lote 2
    "rec_1710a,loja_savassi,pagseguro,card,2026-11-10,2026-11-16,91500,1500,0,90000,PAG-1710,1,2,open",  # K: parcela 1/2
    "rec_1710b,loja_savassi,pagseguro,card,2026-11-10,2026-12-16,91500,1500,0,90000,PAG-1710,2,2,open",  # K: parcela 2/2 adiantada
    "rec_1711,loja_centro,stone,card,2026-11-12,2026-11-14,40000,600,0,39400,STN-1711,1,1,cancelled",  # L: venda cancelada que caiu
]

EXT_LOTE1 = [
    # Semana 03/11
    f"ext_31,T-3101,,2026-10-30T10:15:00-03:00,98500,{STONE},STN-3101,confirmed,settlement",
    f"ext_32,T-3102,,2026-11-02T09:30:00-03:00,61250,{PAG},PAGSEGURO REPASSE,confirmed,settlement",
    # Semana 17/11
    f"ext_41,T-1701,,2026-11-13T11:02:00-03:00,196000,{STONE},STN-1701,confirmed,settlement",
    f"ext_41b,T-1701,,2026-11-13T11:02:07-03:00,196000,{STONE},STN-1701,confirmed,settlement",
    f"ext_42,T-1702,,2026-11-13T08:40:00-03:00,73480,{PAG},PAGSEGURO REPASSE,confirmed,settlement",
    f"ext_44,T-1704,,2026-11-16T14:10:00-03:00,150000,{PAG},PAG-1704 parcial,confirmed,settlement",
    f"ext_45,T-1705,,2026-11-14T10:00:00-03:00,95000,{STONE},STN-1705,confirmed,settlement",
    f"ext_46,T-1706,,2026-11-17T16:00:00-03:00,420000,{STONE},STN-1706,pending,settlement",
    "ext_47,T-1707,,2026-11-15T12:30:00-03:00,35000,ANA LIMA,12345678900,PIX-1707,confirmed,pix_in",
    f"ext_48,T-1708,,2026-11-17T19:30:00-03:00,54320,{PAG},PAG-1708,confirmed,settlement",
    f"ext_49,T-1709,,2026-11-12T13:00:00-03:00,128000,{PAG},PAG-1709,confirmed,settlement",
    "ext_50,T-1750,,2026-11-15T16:20:00-03:00,25000,JOAO PEREIRA,11122233344,PIX RECEBIDO,confirmed,pix_in",
    f"ext_51,T-1710A,,2026-11-16T09:00:00-03:00,90000,{PAG},PAG-1710 1/2,confirmed,settlement",
    f"ext_52,T-1710B,,2026-11-17T10:00:00-03:00,90000,{PAG},PAG-1710 2/2,confirmed,settlement",
    f"ext_53,T-1711,,2026-11-14T15:00:00-03:00,39400,{STONE},STN-1711,confirmed,settlement",
    "ext_54,T-FEE2,,2026-11-17T23:59:00-03:00,350,BANCO INTER,00416968000100,TARIFA PACOTE,confirmed,fee",
]

# ---------- Lote 2: dias depois, chega o que faltava (e um chargeback) ----------

REC_LOTE2: list[str] = []

EXT_LOTE2 = [
    f"ext_61,T-3103,,2026-11-12T10:00:00-03:00,230000,{STONE},STN-3103,confirmed,settlement",  # o não caiu de 03/11 chega
    f"ext_62,T-1704B,,2026-11-18T09:00:00-03:00,100000,{PAG},PAG-1704 complemento,confirmed,settlement",  # o resto do D, depois do corte
    f"ext_63,T-1706,,2026-11-17T17:30:00-03:00,420000,{STONE},STN-1706,confirmed,settlement",  # o pending do F confirma antes do corte
    f"ext_64,T-1709R,T-1709,2026-11-16T11:00:00-03:00,128000,{PAG},CHARGEBACK T-1709,confirmed,chargeback",  # chargeback do I
    f"ext_65,T-4002,,2026-11-11T09:00:00-03:00,500000,{STONE},STN-4002,confirmed,settlement",  # o ext_14 (pending de 10/11) confirma
]


def _base(nome: str) -> bytes:
    """O arquivo de dados/ como está no último commit, com CRLF como no checkout."""
    conteudo = subprocess.run(
        ["git", "show", f"HEAD:dados/{nome}"], cwd=RAIZ, check=True, capture_output=True
    ).stdout
    return conteudo.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def _escrever(pasta: Path, rec: list[str], ext: list[str]) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome in ("lojas.csv", "recebiveis.csv", "extrato.csv"):
        (pasta / nome).write_bytes(_base(nome))
    for nome, linhas in (("recebiveis.csv", rec), ("extrato.csv", ext)):
        if linhas:
            with (pasta / nome).open("ab") as f:  # sem BOM, CRLF como a base
                f.write(("\r\n".join(linhas) + "\r\n").encode("ascii"))


if __name__ == "__main__":
    _escrever(RAIZ / "lote1", REC_LOTE1, EXT_LOTE1)
    _escrever(RAIZ / "lote2", REC_LOTE1 + REC_LOTE2, EXT_LOTE1 + EXT_LOTE2)
    print("ok")
