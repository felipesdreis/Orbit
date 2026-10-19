/** O que acorda o Orbit. A v1 só tem o toque; a v2 acrescenta a wake word sem mexer no resto. */
export interface Ativador {
  onAcordar(cb: () => void): void;
}

export class AtivadorToque implements Ativador {
  constructor(private alvo: HTMLElement) {}

  onAcordar(cb: () => void): void {
    this.alvo.addEventListener('pointerdown', cb);
  }
}
