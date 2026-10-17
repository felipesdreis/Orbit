import { Injectable } from '@angular/core';
import { Fala } from './fala';

type Item = () => Promise<void>;

@Injectable()
export class FalaNavegador extends Fala {
  private fila: Item[] = [];
  private tocando = false;
  private audio?: HTMLAudioElement;
  private esperando: Array<() => void> = [];
  private comecou: () => void = () => {};
  private geracao = 0; // `parar()` invalida o que estava em andamento

  enfileirar(url: string): void {
    this.fila.push(
      () =>
        new Promise<void>((fim) => {
          const audio = new Audio(url);
          this.audio = audio;
          audio.onplaying = () => this.comecou();
          audio.onended = audio.onerror = () => fim();
          audio.play().catch(() => fim()); // sem permissão de áudio: pula, não trava a fila
        }),
    );
    this.andar();
  }

  falarNativo(texto: string): void {
    this.fila.push(
      () =>
        new Promise<void>((fim) => {
          const fala = new SpeechSynthesisUtterance(texto);
          fala.lang = 'pt-BR';
          fala.onstart = () => this.comecou();
          fala.onend = fala.onerror = () => fim();
          speechSynthesis.speak(fala);
        }),
    );
    this.andar();
  }

  ociosa(): Promise<void> {
    return this.tocando || this.fila.length ? new Promise((ok) => this.esperando.push(ok)) : Promise.resolve();
  }

  aoComecar(cb: () => void): void {
    this.comecou = cb;
  }

  parar(): void {
    this.geracao++;
    this.fila = [];
    this.audio?.pause();
    this.audio = undefined;
    speechSynthesis.cancel();
    this.tocando = false;
    this.liberar();
  }

  private async andar(): Promise<void> {
    if (this.tocando) return;
    this.tocando = true;
    const geracao = this.geracao;
    while (this.fila.length && geracao === this.geracao) await this.fila.shift()!();
    if (geracao !== this.geracao) return; // `parar()` já liberou
    this.tocando = false;
    this.liberar();
  }

  private liberar(): void {
    this.esperando.splice(0).forEach((ok) => ok());
  }
}
