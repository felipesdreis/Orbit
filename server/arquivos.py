"""Registro de arquivos servidos em /files/<id>. Só serve o que foi registrado aqui."""
import uuid
from pathlib import Path

_MAX = 200  # guarda os últimos N; áudios antigos são apagados do disco


class Arquivos:
    def __init__(self):
        self._por_id: dict[str, tuple[Path, bool]] = {}

    def registrar(self, caminho: Path, apagar_depois: bool = False) -> str:
        """Registra o arquivo e devolve o nome público (id + extensão)."""
        id_ = uuid.uuid4().hex
        self._por_id[id_] = (caminho, apagar_depois)
        while len(self._por_id) > _MAX:
            velho, apagar = self._por_id.pop(next(iter(self._por_id)))
            if apagar:
                velho.unlink(missing_ok=True)
        return id_ + caminho.suffix

    def buscar(self, nome: str) -> Path | None:
        entrada = self._por_id.get(Path(nome).stem)
        return entrada[0] if entrada and entrada[0].is_file() else None
