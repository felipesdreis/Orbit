import { TestBed } from '@angular/core/testing';
import type { SpeechRecognitionPlugin } from '@capacitor-community/speech-recognition';
import { PLUGIN_STT, SttNativo } from './stt-nativo';

/** Plugin falso: cada `start()` devolve (ou rejeita) o próximo item de `respostas`. */
class PluginFalso {
  disponivel = true;
  permissao = 'granted';
  respostas: Array<{ matches?: string[] } | Error> = [];
  starts = 0;
  paradas = 0;
  pedidos = 0;
  private liberar?: () => void;

  async available() { return { available: this.disponivel }; }
  async checkPermissions() { return { speechRecognition: this.permissao as 'granted' }; }
  async requestPermissions() { this.pedidos++; return { speechRecognition: this.permissao as 'granted' }; }
  async stop() { this.paradas++; this.liberar?.(); }
  start() {
    this.starts++;
    const proxima = this.respostas.shift();
    if (proxima instanceof Error) return Promise.reject(proxima);
    if (proxima) return Promise.resolve(proxima);
    return new Promise<{ matches?: string[] }>((ok) => (this.liberar = () => ok({}))); // sem mais respostas: espera `stop()`
  }
}

const esperar = (ms: number) => new Promise((ok) => setTimeout(ok, ms));

describe('SttNativo', () => {
  let plugin: PluginFalso;
  let stt: SttNativo;
  let frases: string[];
  let erros: string[];

  beforeEach(() => {
    plugin = new PluginFalso();
    TestBed.configureTestingModule({ providers: [SttNativo, { provide: PLUGIN_STT, useValue: plugin as unknown as SpeechRecognitionPlugin }] });
    stt = TestBed.inject(SttNativo);
    frases = [];
    erros = [];
    stt.aoOuvir((t) => frases.push(t));
    stt.aoErro((e) => erros.push(e));
  });

  afterEach(() => stt.parar());

  it('entrega cada frase reconhecida e reinicia sozinho para a seguinte', async () => {
    plugin.respostas = [{ matches: ['orbit como está o pc'] }, { matches: [' e a memória? '] }];
    stt.ouvir();
    await esperar(700);
    expect(frases).toEqual(['orbit como está o pc', 'e a memória?']);
    expect(plugin.starts).toBeGreaterThanOrEqual(3); // continuou ouvindo depois da 2ª frase
  });

  it('silêncio ("No speech input", "No match") não é erro: só ouve de novo', async () => {
    plugin.respostas = [new Error('No speech input'), new Error('No match'), { matches: ['oi'] }];
    stt.ouvir();
    await esperar(900);
    expect(frases).toEqual(['oi']);
    expect(erros).toEqual([]);
  });

  it('pede a permissão do microfone e, se negada, avisa e desiste', async () => {
    plugin.permissao = 'denied';
    stt.ouvir();
    await esperar(50);
    expect(plugin.pedidos).toBe(1);
    expect(plugin.starts).toBe(0);
    expect(erros).toEqual(['not-allowed']);
  });

  it('sem serviço de reconhecimento no aparelho, avisa e desiste', async () => {
    plugin.disponivel = false;
    stt.ouvir();
    await esperar(50);
    expect(erros).toEqual(['service-unavailable']);
    expect(plugin.starts).toBe(0);
  });

  it('erros de rede e de áudio são repassados, e o ciclo segue tentando', async () => {
    plugin.respostas = [new Error('Network error'), new Error('Audio recording error')];
    stt.ouvir();
    await esperar(3300);
    expect(erros).toEqual(['network', 'audio-capture']);
    expect(plugin.starts).toBeGreaterThanOrEqual(3);
  });

  it('permissão negada no meio do uso para o ciclo', async () => {
    plugin.respostas = [new Error('Missing permission')];
    stt.ouvir();
    await esperar(100);
    expect(erros).toEqual(['not-allowed']);
    const starts = plugin.starts;
    await esperar(1800);
    expect(plugin.starts).toBe(starts); // não ficou insistindo
  });

  it('parar() interrompe o ciclo e ignora a frase que chegar depois', async () => {
    stt.ouvir();
    await esperar(50);
    stt.parar();
    expect(plugin.paradas).toBe(1);
    await esperar(400);
    const starts = plugin.starts;
    await esperar(600);
    expect(plugin.starts).toBe(starts);
    expect(frases).toEqual([]);
  });

  it('ouvir() de novo logo depois de parar() não cria dois ciclos', async () => {
    stt.ouvir();
    await esperar(30);
    stt.parar();
    stt.ouvir();
    stt.ouvir();
    await esperar(400);
    expect(plugin.starts).toBeLessThanOrEqual(3); // um ciclo só: dois ciclos teriam bem mais starts
  });
});
