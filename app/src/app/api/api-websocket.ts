import { Injectable, signal } from '@angular/core';
import { Api } from './api';
import { MsgServidor } from './mensagens';

const PORTA = 8765;
const RECONECTAR_MS = 2000;
const CHAVE = 'orbit.pc';

/** "192.168.0.10", "http://192.168.0.10:8765/" ou "ws://pc" viram "192.168.0.10:8765", "192.168.0.10:8765", "pc:8765". */
export function normalizarEndereco(texto: string): string {
  const limpo = texto.trim().replace(/^[a-z]+:\/\//i, '').replace(/\/.*$/, '');
  return !limpo || limpo.includes(':') ? limpo : `${limpo}:${PORTA}`;
}

/** Endereço do PC: o salvo (ou `?pc=192.168.0.10`); sem isso, o mesmo host que serviu a página. */
export function enderecoDoServidor(): string {
  let pc = new URLSearchParams(location.search).get('pc');
  try {
    if (pc) localStorage.setItem(CHAVE, pc);
    else pc = localStorage.getItem(CHAVE);
  } catch {
    // localStorage pode estar bloqueado; segue sem lembrar
  }
  return normalizarEndereco(pc || location.hostname);
}

@Injectable()
export class ApiWebSocket extends Api {
  readonly conectado = signal(false);
  readonly servidor = signal(enderecoDoServidor());
  private socket?: WebSocket;
  private ouvinte: (msg: MsgServidor) => void = () => {};

  conectar(): void {
    if (this.socket && this.socket.readyState <= WebSocket.OPEN) return;
    const socket = new WebSocket(`ws://${this.servidor()}/ws`);
    this.socket = socket;
    socket.onopen = () => this.conectado.set(true);
    socket.onmessage = (e) => this.ouvinte(JSON.parse(e.data));
    socket.onclose = () => {
      this.conectado.set(false);
      if (this.socket === socket) setTimeout(() => this.conectar(), RECONECTAR_MS); // trocado de propósito: não reabre o antigo
    };
  }

  definirServidor(endereco: string): void {
    const novo = normalizarEndereco(endereco);
    if (!novo) return;
    try {
      localStorage.setItem(CHAVE, novo);
    } catch {
      // sem localStorage: vale só até fechar o app
    }
    this.servidor.set(novo);
    const antigo = this.socket;
    this.socket = undefined;
    this.conectado.set(false);
    antigo?.close();
    this.conectar();
  }

  enviarFala(texto: string): boolean {
    if (this.socket?.readyState !== WebSocket.OPEN) return false;
    this.socket.send(JSON.stringify({ type: 'fala', text: texto }));
    return true;
  }

  aoReceber(cb: (msg: MsgServidor) => void): void {
    this.ouvinte = cb;
  }
}
