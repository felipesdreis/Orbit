import { Injectable, inject, signal } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { Api } from '../api/api';
import { MsgServidor } from '../api/mensagens';
import { Emocao, Estado } from '../face/face.types';
import { Fala } from './fala';
import { contemOrbit } from './nome';
import { Stt } from './stt';

export const ATIVO_MS = 15 * 60_000; // sem fala por 15 min, volta ao standby
export const FOLLOWUP_MS = 25_000; // depois de uma resposta, o nome não é exigido
export const ESPERA_MAX_MS = 90_000; // se o servidor não terminar a vez, volta a ouvir
export const LEGENDA_IGNORADA_MS = 8_000; // frase sem o nome: a legenda some depois disso
export const LEGENDA_APOS_RESPOSTA_MS = 5_000; // frase enviada: a legenda some depois que ele volta a ouvir

/** Orquestra a conversa: ativação, escuta, filtro do nome, servidor e voz (half-duplex). */
@Injectable({ providedIn: 'root' })
export class OrbitService {
  private api = inject(Api);
  private stt = inject(Stt);
  private fala = inject(Fala);

  readonly estado = signal<Estado>('standby');
  readonly emocao = signal<Emocao>('neutro');
  readonly imagem = signal<string | null>(null);
  readonly aviso = signal<string | null>(null);
  /** Última frase reconhecida e o que se fez com ela (ajuda a depurar o filtro do nome). */
  readonly ouvido = signal<{ texto: string; enviado: boolean } | null>(null);
  /** O que ele entendeu, para a tela principal: some sozinha (ver `registrarOuvido` e `voltarAOuvir`). */
  readonly legenda = signal<{ texto: string; enviado: boolean } | null>(null);

  private expira?: ReturnType<typeof setTimeout>;
  private apagaLegenda?: ReturnType<typeof setTimeout>;
  private vigia?: ReturnType<typeof setTimeout>;
  private semNomeAte = 0;
  private wakeLock?: { release(): Promise<void> };

  constructor() {
    this.stt.aoOuvir((texto) => this.aoOuvir(texto));
    this.stt.aoErro((erro) => this.aoErroStt(erro));
    this.api.aoReceber((msg) => this.aoReceber(msg));
    this.fala.aoComecar(() => {
      if (this.estado() === 'pensando') this.estado.set('falando');
    });
    this.api.conectar();
    document.addEventListener('visibilitychange', () => {
      // No APK, ir para segundo plano libera o microfone (o Android não deixa um app em segundo plano ouvir).
      if (document.hidden && Capacitor.isNativePlatform()) this.dormir();
      else if (this.estado() !== 'standby') void this.segurarTela();
    });
  }

  /** Toque na tela: acorda; já acordado, só renova o prazo. */
  acordar(): void {
    this.aviso.set(null);
    this.fala.preparar(); // dentro do toque: é o que libera o áudio do navegador
    if (this.estado() !== 'standby') return this.renovar();
    if (!this.stt.suportado) return this.aviso.set('Este navegador não tem reconhecimento de voz. Use o Chrome.');
    this.estado.set('ouvindo');
    this.emocao.set('neutro');
    this.semNomeAte = 0;
    this.renovar();
    this.segurarTela();
    this.stt.ouvir();
  }

  dormir(): void {
    clearTimeout(this.expira);
    clearTimeout(this.vigia);
    this.stt.parar();
    this.fala.parar();
    this.estado.set('standby');
    this.emocao.set('neutro');
    this.imagem.set(null);
    clearTimeout(this.apagaLegenda);
    this.legenda.set(null);
    this.wakeLock?.release().catch(() => {});
    this.wakeLock = undefined;
  }

  private renovar(): void {
    clearTimeout(this.expira);
    this.expira = setTimeout(() => this.dormir(), ATIVO_MS);
  }

  private aoOuvir(texto: string): void {
    if (this.estado() !== 'ouvindo') return; // half-duplex: ignora o que chegar enquanto ele fala
    this.renovar(); // qualquer fala reconhecida mostra que há gente por perto
    const dentroDoFollowup = Date.now() < this.semNomeAte;
    if (!dentroDoFollowup && !contemOrbit(texto)) return this.registrarOuvido(texto, false);
    if (!this.api.enviarFala(texto)) {
      this.registrarOuvido(texto, false);
      return this.aviso.set('Sem conexão com o PC. Confira se o servidor está rodando e o endereço do PC em ⚙.');
    }
    this.registrarOuvido(texto, true);
    this.aviso.set(null);
    this.imagem.set(null);
    this.estado.set('pensando');
    this.stt.parar();
    clearTimeout(this.vigia);
    this.vigia = setTimeout(() => this.voltarAOuvir(), ESPERA_MAX_MS);
  }

  /** Guarda o que foi ouvido. Frase enviada: a legenda fica até a vez terminar; ignorada: some logo. */
  private registrarOuvido(texto: string, enviado: boolean): void {
    this.ouvido.set({ texto, enviado });
    this.legenda.set({ texto, enviado });
    this.apagarLegendaEm(enviado ? undefined : LEGENDA_IGNORADA_MS);
  }

  private apagarLegendaEm(ms?: number): void {
    clearTimeout(this.apagaLegenda);
    if (ms !== undefined) this.apagaLegenda = setTimeout(() => this.legenda.set(null), ms);
  }

  private aoErroStt(erro: string): void {
    if (erro === 'not-allowed' || erro === 'service-not-allowed') {
      this.aviso.set('Microfone bloqueado. Libere a permissão do microfone no navegador.');
      this.dormir();
    } else if (erro === 'service-unavailable') {
      this.aviso.set('Este aparelho não tem reconhecimento de voz. Instale ou atualize o app Google.');
      this.dormir();
    } else if (erro === 'network') {
      this.aviso.set('O reconhecimento de voz precisa de internet (ou do pacote de voz offline em português).');
    } else if (erro === 'audio-capture') {
      this.aviso.set('Não consegui usar o microfone. Outro app pode estar usando.');
    }
  }

  private aoReceber(msg: MsgServidor): void {
    if (this.estado() === 'standby') return; // chegou depois de dormir
    switch (msg.type) {
      case 'pensando':
        this.estado.set('pensando');
        break;
      case 'resposta':
        this.emocao.set(msg.emocao);
        if (!msg.audio) this.fala.falarNativo(msg.text);
        break;
      case 'imagem':
        this.imagem.set(msg.url);
        break;
      case 'audio':
        this.fala.enfileirar(msg.url);
        break;
      case 'fim':
        void this.fala.ociosa().then(() => this.voltarAOuvir());
        break;
    }
  }

  /** Terminou de falar: abre a janela de follow-up e volta a ouvir. */
  private voltarAOuvir(): void {
    clearTimeout(this.vigia);
    if (this.estado() === 'standby' || this.estado() === 'ouvindo') return;
    this.semNomeAte = Date.now() + FOLLOWUP_MS;
    this.apagarLegendaEm(LEGENDA_APOS_RESPOSTA_MS);
    this.estado.set('ouvindo');
    this.emocao.set('neutro');
    this.renovar();
    this.stt.ouvir();
  }

  private async segurarTela(): Promise<void> {
    try {
      await this.wakeLock?.release(); // evita acumular travas ao voltar para a aba
      this.wakeLock = await (navigator as any).wakeLock?.request('screen');
    } catch {
      // sem suporte ou negado: a tela pode apagar sozinha
    }
  }
}
