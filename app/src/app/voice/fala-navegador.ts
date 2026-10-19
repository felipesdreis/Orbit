import { Injectable } from '@angular/core';
import { Fala } from './fala';

const FOLGA_S = 0.03; // margem para agendar o 1º trecho sem cortar o começo

/**
 * Fala do Orbit pelo Web Audio. Cada WAV do servidor é baixado e decodificado inteiro (em paralelo
 * com o que está tocando) e os trechos são agendados um colado no outro. Tocar da memória evita o
 * engasgo no meio das palavras que o streaming de um <audio> sofre quando a CPU está ocupada.
 */
@Injectable()
export class FalaNavegador extends Fala {
  private ctx?: AudioContext;
  private fontes = new Set<AudioBufferSourceNode>();
  private fimAgendado = 0; // instante (relógio do AudioContext) em que o último trecho agendado termina
  private pendentes = 0; // trechos ainda baixando/decodificando + falas nativas em andamento
  private cadeia: Promise<void> = Promise.resolve(); // mantém os trechos na ordem em que chegaram
  private esperando: Array<() => void> = [];
  private comecou: () => void = () => {};
  private geracao = 0; // `parar()` invalida o que estava em andamento

  preparar(): void {
    this.ctx ??= new AudioContext({ latencyHint: 'playback' }); // buffer maior: prefere folga a baixa latência
    void this.ctx.resume();
  }

  enfileirar(url: string): void {
    this.preparar();
    const ctx = this.ctx!;
    const geracao = this.geracao;
    this.pendentes++;
    const audio = fetch(url)
      .then((r) => r.arrayBuffer())
      .then((b) => ctx.decodeAudioData(b))
      .catch(() => null); // trecho que falhou é pulado, não trava a fila
    this.cadeia = this.cadeia.then(async () => {
      const buffer = await audio;
      if (geracao !== this.geracao) return;
      this.pendentes--;
      if (buffer) this.agendar(ctx, buffer);
      this.liberarSeOciosa();
    });
  }

  falarNativo(texto: string): void {
    const geracao = this.geracao;
    this.pendentes++;
    const fala = new SpeechSynthesisUtterance(texto);
    fala.lang = 'pt-BR';
    fala.onstart = () => geracao === this.geracao && this.comecou();
    fala.onend = fala.onerror = () => {
      if (geracao !== this.geracao) return;
      this.pendentes--;
      this.liberarSeOciosa();
    };
    speechSynthesis.speak(fala);
  }

  ociosa(): Promise<void> {
    return this.ocioso() ? Promise.resolve() : new Promise((ok) => this.esperando.push(ok));
  }

  aoComecar(cb: () => void): void {
    this.comecou = cb;
  }

  parar(): void {
    this.geracao++;
    this.fontes.forEach((f) => {
      f.onended = null;
      try {
        f.stop();
      } catch {
        // ainda não tinha começado
      }
    });
    this.fontes.clear();
    this.cadeia = Promise.resolve();
    this.fimAgendado = 0;
    this.pendentes = 0;
    speechSynthesis.cancel();
    this.liberar();
  }

  private agendar(ctx: AudioContext, buffer: AudioBuffer): void {
    const fonte = ctx.createBufferSource();
    fonte.buffer = buffer;
    fonte.connect(ctx.destination);
    const inicio = Math.max(ctx.currentTime + FOLGA_S, this.fimAgendado); // cola no fim do trecho anterior
    const primeiro = this.fontes.size === 0;
    fonte.start(inicio);
    this.fimAgendado = inicio + buffer.duration;
    this.fontes.add(fonte);
    fonte.onended = () => {
      this.fontes.delete(fonte);
      this.liberarSeOciosa();
    };
    if (primeiro) {
      const geracao = this.geracao;
      setTimeout(() => geracao === this.geracao && this.comecou(), (inicio - ctx.currentTime) * 1000);
    }
  }

  private ocioso(): boolean {
    return this.pendentes === 0 && this.fontes.size === 0;
  }

  private liberarSeOciosa(): void {
    if (this.ocioso()) this.liberar();
  }

  private liberar(): void {
    this.esperando.splice(0).forEach((ok) => ok());
  }
}
