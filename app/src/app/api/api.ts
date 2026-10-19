import { Signal } from '@angular/core';
import { MsgServidor } from './mensagens';

/** Conexão com o servidor do PC. Abstrata para os testes trocarem por uma falsa. */
export abstract class Api {
  abstract readonly conectado: Signal<boolean>;
  /** Endereço do PC em uso (IP ou IP:porta). */
  abstract readonly servidor: Signal<string>;
  abstract conectar(): void;
  /** Troca o endereço do PC (fica salvo) e reconecta. */
  abstract definirServidor(endereco: string): void;
  /** Devolve false se não houver conexão (a fala não foi enviada). */
  abstract enviarFala(texto: string): boolean;
  abstract aoReceber(cb: (msg: MsgServidor) => void): void;
}
