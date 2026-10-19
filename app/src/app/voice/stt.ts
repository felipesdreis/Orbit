/** Reconhecimento de fala. Abstrato para os testes trocarem por um falso. */
export abstract class Stt {
  abstract readonly suportado: boolean;
  /** Começa a ouvir e reinicia sozinho até `parar()`. Cada frase final chega em `aoOuvir`. */
  abstract ouvir(): void;
  abstract parar(): void;
  abstract aoOuvir(cb: (texto: string) => void): void;
  abstract aoErro(cb: (erro: string) => void): void;
}
