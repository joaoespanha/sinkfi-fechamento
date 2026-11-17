"""Escreve o OpenAPI do app na saída padrão, sem subir servidor: `python -m sinkfi.exportar_openapi`.

O `web` gera `src/api.d.ts` a partir dele (`npm run contrato`).
"""

import json
import sys

from sinkfi.api import app

if __name__ == "__main__":
    json.dump(app.openapi(), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
