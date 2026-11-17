"""Leva o banco de DATABASE_URL até a última migração: `python -m sinkfi.migrar`."""

import os

from sinkfi.banco import migrar

if __name__ == "__main__":
    migrar(os.environ["DATABASE_URL"])
