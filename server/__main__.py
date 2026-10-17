"""Sobe o servidor: `python -m server` (porta 8765, aberta na rede local)."""
import logging
import os
import sys

import uvicorn

# No Windows, com a saída redirecionada para arquivo, o padrão não é UTF-8 e o "º" sai quebrado.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
uvicorn.run("server.main:criar_app", factory=True, host="0.0.0.0", port=int(os.environ.get("ORBIT_PORTA", "8765")))
