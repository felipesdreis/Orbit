import { Injectable, InjectionToken, inject } from '@angular/core';
import { SpeechRecognition, SpeechRecognitionPlugin } from '@capacitor-community/speech-recognition';
import { Stt } from './stt';

/** O plugin nativo; os testes trocam por um falso. */
export const PLUGIN_STT = new InjectionToken<SpeechRecognitionPlugin>('PLUGIN_STT');

const REINICIAR_MS = 250;
const REINICIAR_OCUPADO_MS = 800;
const REINICIAR_ERRO_MS = 1500;

/**
 * STT do Android (SpeechRecognizer) pelo plugin do Capacitor, para o APK. O `start()` do plugin só
 * responde quando o Android entrega a frase (ou rejeita com um texto), então o ciclo é sequencial:
 * duas chamadas ao mesmo tempo destruiriam o reconhecedor anterior.
 */
@Injectable()
export class SttNativo extends Stt {
  readonly suportado = true; // a disponibilidade real é checada ao começar a ouvir
  private plugin = inject(PLUGIN_STT, { optional: true }) ?? SpeechRecognition;
  private ativo = false;
  private rodando = false;
  private ouvinteTexto: (t: string) => void = () => {};
  private ouvinteErro: (e: string) => void = () => {};

  ouvir(): void {
    this.ativo = true;
    void this.ciclo(); // se o ciclo já está rodando, só continua valendo `ativo`
  }

  parar(): void {
    this.ativo = false;
    void this.plugin.stop().catch(() => {}); // não estava ouvindo: tudo bem
  }

  aoOuvir(cb: (texto: string) => void): void {
    this.ouvinteTexto = cb;
  }

  aoErro(cb: (erro: string) => void): void {
    this.ouvinteErro = cb;
  }

  private async ciclo(): Promise<void> {
    if (this.rodando) return;
    this.rodando = true;
    try {
      if (!(await this.preparar())) return;
      while (this.ativo) {
        let espera = REINICIAR_MS;
        try {
          const r = await this.plugin.start({ language: 'pt-BR', maxResults: 1, partialResults: false, popup: false });
          const texto = r.matches?.[0]?.trim();
          if (texto && this.ativo) this.ouvinteTexto(texto);
        } catch (erro) {
          espera = this.tratar(erro);
        }
        await new Promise((ok) => setTimeout(ok, espera));
      }
    } finally {
      this.rodando = false;
    }
  }

  /** Confere o serviço de voz e a permissão do microfone. Sem uma das duas, avisa e desiste. */
  private async preparar(): Promise<boolean> {
    if (!(await this.plugin.available()).available) {
      this.desistir('service-unavailable');
      return false;
    }
    let permissao = await this.plugin.checkPermissions();
    if (permissao.speechRecognition !== 'granted') permissao = await this.plugin.requestPermissions();
    if (permissao.speechRecognition !== 'granted') {
      this.desistir('not-allowed');
      return false;
    }
    return true;
  }

  private desistir(erro: string): void {
    this.ativo = false;
    this.ouvinteErro(erro);
  }

  /** Traduz o texto de erro do plugin; devolve quanto esperar antes de ouvir de novo. */
  private tratar(erro: unknown): number {
    const msg = String((erro as { message?: string })?.message ?? erro);
    if (/no match|no speech/i.test(msg)) return REINICIAR_MS; // silêncio é normal
    if (/busy/i.test(msg)) return REINICIAR_OCUPADO_MS;
    if (/permission/i.test(msg)) {
      this.desistir('not-allowed');
      return REINICIAR_ERRO_MS;
    }
    if (/not available/i.test(msg)) {
      this.desistir('service-unavailable');
      return REINICIAR_ERRO_MS;
    }
    if (/network|server/i.test(msg)) this.ouvinteErro('network');
    else if (/audio/i.test(msg)) this.ouvinteErro('audio-capture');
    return REINICIAR_ERRO_MS;
  }
}
