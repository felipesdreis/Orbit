import { Emocao } from '../face/face.types';

/** Mensagens que o servidor envia ao tablet (ver README, "Protocolo"). */
export type MsgServidor =
  | { type: 'pensando' }
  | { type: 'resposta'; text: string; emocao: Emocao; audio: boolean }
  | { type: 'imagem'; url: string }
  | { type: 'audio'; url: string }
  | { type: 'fim' };
