"""A hora de cada requisição. Os testes trocam `obter_agora` por `dependency_overrides`."""

from datetime import UTC, datetime


def obter_agora() -> datetime:
    return datetime.now(UTC)
