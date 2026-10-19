import { Injectable } from '@angular/core';
import { Stt } from './stt';

const REINICIAR_MS = 250;
const REINICIAR_ERRO_MS = 1500;

// A Web Speech API ainda não está nos tipos do TypeScript.
const Reconhecimento = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;

/** STT pelo navegador (Web Speech API). No APK (etapa 4) entra o plugin nativo no lugar. */
@Injectable()
export class SttWebSpeech extends Stt {
  readonly suportado = !!Reconhecimento;
  private ativo = false;
  private rec: any;
  private reinicio?: ReturnType<typeof setTimeout>;
  private ouvinteTexto: (t: string) => void = () => {};
  private ouvinteErro: (e: string) => void = () => {};

  ouvir(): void {
    if (!this.suportado || this.ativo) return;
    this.ativo = true;
    this.iniciar();
  }

  parar(): void {
    this.ativo = false;
    clearTimeout(this.reinicio);
    try {
      this.rec?.abort();
    } catch {
      // já estava parado
    }
    this.rec = undefined;
  }

  aoOuvir(cb: (texto: string) => void): void {
    this.ouvinteTexto = cb;
  }

  aoErro(cb: (erro: string) => void): void {
    this.ouvinteErro = cb;
  }

  private iniciar(): void {
    const rec = new Reconhecimento();
    this.rec = rec;
    rec.lang = 'pt-BR';
    rec.continuous = false; // o navegador encerra no silêncio; o `onend` reinicia
    rec.interimResults = false;
    let comErro = false;
    rec.onresult = (e: any) => {
      const texto = e.results[e.results.length - 1]?.[0]?.transcript?.trim();
      if (texto && this.ativo) this.ouvinteTexto(texto);
    };
    rec.onerror = (e: any) => {
      if (e.error === 'no-speech' || e.error === 'aborted') return; // silêncio é normal
      comErro = true;
      this.ouvinteErro(e.error); // 'not-allowed', 'network', 'audio-capture'...
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') this.ativo = false;
    };
    rec.onend = () => {
      if (!this.ativo || this.rec !== rec) return;
      this.reinicio = setTimeout(() => this.ativo && this.iniciar(), comErro ? REINICIAR_ERRO_MS : REINICIAR_MS);
    };
    try {
      rec.start();
    } catch {
      this.reinicio = setTimeout(() => this.ativo && this.iniciar(), REINICIAR_ERRO_MS);
    }
  }
}
