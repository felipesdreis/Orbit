/** Saída de voz: fila de áudios do servidor e voz nativa (fallback). Abstrata para os testes. */
export abstract class Fala {
  /** Libera o áudio do navegador. Chamar dentro de um toque do usuário (a política de autoplay exige). */
  abstract preparar(): void;
  /** Toca o áudio do servidor depois dos que já estão na fila. */
  abstract enfileirar(url: string): void;
  /** Fala o texto com a voz do aparelho (servidor sem Kokoro ou com erro). */
  abstract falarNativo(texto: string): void;
  /** Resolve quando a fila esvaziar e nada estiver tocando. */
  abstract ociosa(): Promise<void>;
  /** Avisa quando o som de fato começa (para a boca só mexer com voz). */
  abstract aoComecar(cb: () => void): void;
  /** Corta o que estiver tocando e esvazia a fila. */
  abstract parar(): void;
}
