import { Injectable, signal } from '@angular/core';
import { Api } from './api';
import { MsgServidor } from './mensagens';

const PORTA = 8765;
const RECONECTAR_MS = 2000;

/** Endereço do PC: `?pc=192.168.0.10` (fica salvo); sem isso, o mesmo host que serviu a página. */
export function urlDoServidor(): string {
  let pc = new URLSearchParams(location.search).get('pc');
  try {
    if (pc) localStorage.setItem('orbit.pc', pc);
    else pc = localStorage.getItem('orbit.pc');
  } catch {
    // localStorage pode estar bloqueado; segue sem lembrar
  }
  return `ws://${pc || location.hostname}:${PORTA}/ws`;
}

@Injectable()
export class ApiWebSocket extends Api {
  readonly conectado = signal(false);
  private socket?: WebSocket;
  private ouvinte: (msg: MsgServidor) => void = () => {};

  conectar(): void {
    if (this.socket && this.socket.readyState <= WebSocket.OPEN) return;
    const socket = new WebSocket(urlDoServidor());
    this.socket = socket;
    socket.onopen = () => this.conectado.set(true);
    socket.onmessage = (e) => this.ouvinte(JSON.parse(e.data));
    socket.onclose = () => {
      this.conectado.set(false);
      setTimeout(() => this.conectar(), RECONECTAR_MS);
    };
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
