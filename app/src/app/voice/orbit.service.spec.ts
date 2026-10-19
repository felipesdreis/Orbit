import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Api } from '../api/api';
import { MsgServidor } from '../api/mensagens';
import { Fala } from './fala';
import { ATIVO_MS, ESPERA_MAX_MS, FOLLOWUP_MS, OrbitService } from './orbit.service';
import { Stt } from './stt';

class SttFalso extends Stt {
  suportado = true;
  ouvindo = false;
  private texto: (t: string) => void = () => {};
  private erro: (e: string) => void = () => {};
  ouvir() { this.ouvindo = true; }
  parar() { this.ouvindo = false; }
  aoOuvir(cb: (t: string) => void) { this.texto = cb; }
  aoErro(cb: (e: string) => void) { this.erro = cb; }
  dizer(t: string) { this.texto(t); }
  falhar(e: string) { this.erro(e); }
}

class ApiFalsa extends Api {
  conectado = signal(true);
  servidor = signal('pc:8765');
  enviadas: string[] = [];
  private cb: (m: MsgServidor) => void = () => {};
  conectar() {}
  definirServidor(e: string) { this.servidor.set(e); }
  enviarFala(t: string) {
    if (!this.conectado()) return false;
    this.enviadas.push(t);
    return true;
  }
  aoReceber(cb: (m: MsgServidor) => void) { this.cb = cb; }
  receber(m: MsgServidor) { this.cb(m); }
}

class FalaFalsa extends Fala {
  urls: string[] = [];
  nativas: string[] = [];
  paradas = 0;
  preparou = 0;
  private liberar: Array<() => void> = [];
  private comecou: () => void = () => {};
  preparar() { this.preparou++; }
  enfileirar(url: string) { this.urls.push(url); }
  falarNativo(t: string) { this.nativas.push(t); }
  ociosa() { return new Promise<void>((ok) => this.liberar.push(ok)); }
  aoComecar(cb: () => void) { this.comecou = cb; }
  parar() { this.paradas++; }
  terminarDeFalar() { this.liberar.splice(0).forEach((ok) => ok()); }
  comecarASoar() { this.comecou(); }
}

const virar = async () => { for (let i = 0; i < 5; i++) await Promise.resolve(); };

describe('OrbitService', () => {
  let orbit: OrbitService, stt: SttFalso, api: ApiFalsa, fala: FalaFalsa;

  beforeEach(() => {
    jasmine.clock().install();
    jasmine.clock().mockDate(new Date(2026, 0, 1));
    TestBed.configureTestingModule({
      providers: [
        { provide: Stt, useClass: SttFalso },
        { provide: Api, useClass: ApiFalsa },
        { provide: Fala, useClass: FalaFalsa },
      ],
    });
    orbit = TestBed.inject(OrbitService);
    stt = TestBed.inject(Stt) as SttFalso;
    api = TestBed.inject(Api) as ApiFalsa;
    fala = TestBed.inject(Fala) as FalaFalsa;
  });
  afterEach(() => jasmine.clock().uninstall());

  const tempo = (ms: number) => jasmine.clock().tick(ms);

  /** O servidor responde, o áudio toca até o fim e o Orbit volta a ouvir. */
  async function responderServidor(resposta = 'Tudo certo.') {
    api.receber({ type: 'pensando' });
    api.receber({ type: 'resposta', text: resposta, emocao: 'feliz', audio: true });
    api.receber({ type: 'audio', url: 'http://pc/files/a.wav' });
    api.receber({ type: 'fim' });
    fala.terminarDeFalar();
    await virar();
  }

  async function conversar(texto = 'orbit como está o pc', resposta = 'Tudo certo.') {
    orbit.acordar();
    stt.dizer(texto);
    await responderServidor(resposta);
  }

  it('começa em standby e o toque acorda e liga o microfone', () => {
    expect(orbit.estado()).toBe('standby');
    expect(stt.ouvindo).toBeFalse();
    orbit.acordar();
    expect(orbit.estado()).toBe('ouvindo');
    expect(stt.ouvindo).toBeTrue();
  });

  it('o toque libera o áudio do navegador', () => {
    orbit.acordar();
    expect(fala.preparou).toBe(1);
  });

  it('sem reconhecimento de voz, avisa e continua em standby', () => {
    stt.suportado = false;
    orbit.acordar();
    expect(orbit.estado()).toBe('standby');
    expect(orbit.aviso()).toContain('reconhecimento de voz');
  });

  it('ignora frase sem o nome e envia a que tem o nome', () => {
    orbit.acordar();
    stt.dizer('que horas são');
    expect(api.enviadas).toEqual([]);
    expect(orbit.ouvido()).toEqual({ texto: 'que horas são', enviado: false });
    stt.dizer('Órbita, que horas são');
    expect(api.enviadas).toEqual(['Órbita, que horas são']);
    expect(orbit.estado()).toBe('pensando');
  });

  it('half-duplex: para de ouvir ao enviar e ignora o que chegar enquanto pensa ou fala', () => {
    orbit.acordar();
    stt.dizer('orbit oi');
    expect(stt.ouvindo).toBeFalse();
    stt.dizer('orbit isso é eco da própria voz');
    expect(api.enviadas.length).toBe(1);
  });

  it('o rosto só passa a falar quando o som começa, e usa a emoção da resposta', async () => {
    orbit.acordar();
    stt.dizer('orbit oi');
    api.receber({ type: 'resposta', text: 'Oi!', emocao: 'feliz', audio: true });
    api.receber({ type: 'audio', url: 'http://pc/files/a.wav' });
    expect(orbit.estado()).toBe('pensando');
    expect(orbit.emocao()).toBe('feliz');
    expect(fala.urls).toEqual(['http://pc/files/a.wav']);
    fala.comecarASoar();
    expect(orbit.estado()).toBe('falando');
  });

  it('só volta a ouvir depois do fim e de o último áudio terminar', async () => {
    orbit.acordar();
    stt.dizer('orbit oi');
    api.receber({ type: 'resposta', text: 'Oi!', emocao: 'neutro', audio: true });
    api.receber({ type: 'audio', url: 'http://pc/files/a.wav' });
    fala.comecarASoar();
    await virar();
    expect(stt.ouvindo).toBeFalse(); // ainda falando: sem `fim`, não volta
    api.receber({ type: 'fim' });
    await virar();
    expect(stt.ouvindo).toBeFalse(); // `fim` chegou, mas o áudio ainda toca
    fala.terminarDeFalar();
    await virar();
    expect(orbit.estado()).toBe('ouvindo');
    expect(orbit.emocao()).toBe('neutro');
    expect(stt.ouvindo).toBeTrue();
  });

  it('servidor sem Kokoro (audio:false): fala com a voz nativa', () => {
    orbit.acordar();
    stt.dizer('orbit oi');
    api.receber({ type: 'resposta', text: 'Oi, tudo bem?', emocao: 'neutro', audio: false });
    expect(fala.nativas).toEqual(['Oi, tudo bem?']);
  });

  it('follow-up: sem o nome só vale por 25 s depois da resposta', async () => {
    await conversar();
    expect(orbit.estado()).toBe('ouvindo');
    tempo(FOLLOWUP_MS - 1000);
    stt.dizer('e a memória?');
    expect(api.enviadas).toEqual(['orbit como está o pc', 'e a memória?']);
    await responderServidor('Certo.');

    await conversar('orbit de novo', 'Certo.');
    tempo(FOLLOWUP_MS + 1000);
    stt.dizer('fora da janela');
    expect(api.enviadas.length).toBe(3); // ignorada: passou da janela e não tem o nome
    stt.dizer('orbit agora com o nome');
    expect(api.enviadas.length).toBe(4);
  });

  it('15 min sem fala voltam ao standby; fala reconhecida renova o prazo', () => {
    orbit.acordar();
    tempo(ATIVO_MS - 60_000);
    stt.dizer('conversa de outra pessoa'); // ignorada pelo filtro, mas renova
    tempo(ATIVO_MS - 60_000);
    expect(orbit.estado()).toBe('ouvindo');
    tempo(61_000);
    expect(orbit.estado()).toBe('standby');
    expect(stt.ouvindo).toBeFalse();
    expect(fala.paradas).toBeGreaterThan(0);
  });

  it('mensagens que chegam depois de dormir são ignoradas', () => {
    orbit.acordar();
    orbit.dormir();
    api.receber({ type: 'audio', url: 'http://pc/files/a.wav' });
    api.receber({ type: 'imagem', url: 'http://pc/files/a.png' });
    expect(fala.urls).toEqual([]);
    expect(orbit.imagem()).toBeNull();
  });

  it('mostra a imagem enviada e a limpa na próxima fala', async () => {
    orbit.acordar();
    stt.dizer('orbit mostra a tela');
    api.receber({ type: 'imagem', url: 'http://pc/files/tela.png' });
    expect(orbit.imagem()).toBe('http://pc/files/tela.png');
    api.receber({ type: 'fim' });
    fala.terminarDeFalar();
    await virar();
    expect(orbit.imagem()).toBe('http://pc/files/tela.png'); // continua na tela enquanto ele espera
    stt.dizer('orbit e agora?'); // follow-up
    expect(orbit.imagem()).toBeNull();
  });

  it('sem conexão com o PC: avisa, não envia e continua ouvindo', () => {
    api.conectado.set(false);
    orbit.acordar();
    stt.dizer('orbit oi');
    expect(api.enviadas).toEqual([]);
    expect(orbit.aviso()).toContain('Sem conexão');
    expect(orbit.estado()).toBe('ouvindo');
    expect(stt.ouvindo).toBeTrue();
  });

  it('se o servidor nunca mandar o fim, volta a ouvir depois de um tempo', () => {
    orbit.acordar();
    stt.dizer('orbit oi');
    expect(orbit.estado()).toBe('pensando');
    tempo(ESPERA_MAX_MS + 1000);
    expect(orbit.estado()).toBe('ouvindo');
    expect(stt.ouvindo).toBeTrue();
  });

  it('sem serviço de reconhecimento de voz no aparelho: avisa e volta ao standby', () => {
    orbit.acordar();
    stt.falhar('service-unavailable');
    expect(orbit.aviso()).toContain('reconhecimento de voz');
    expect(orbit.estado()).toBe('standby');
  });

  it('erro de microfone ocupado só avisa e continua ouvindo', () => {
    orbit.acordar();
    stt.falhar('audio-capture');
    expect(orbit.aviso()).toContain('microfone');
    expect(orbit.estado()).toBe('ouvindo');
  });

  it('microfone bloqueado: avisa e volta ao standby', () => {
    orbit.acordar();
    stt.falhar('not-allowed');
    expect(orbit.aviso()).toContain('Microfone bloqueado');
    expect(orbit.estado()).toBe('standby');
  });
});
