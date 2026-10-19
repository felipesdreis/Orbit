"""Configuração dos testes: deixa `import minha_tool` funcionar para os arquivos de tools/."""
import sys
from pathlib import Path

# `append` (e nunca `insert(0, ...)`): tools/server.py (o servidor MCP) esconderia o pacote server/
# se tools/ ficasse na frente do caminho de importação.
sys.path.append(str(Path(__file__).resolve().parent.parent / "tools"))
