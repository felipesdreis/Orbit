import { normalizarEndereco } from './api-websocket';

describe('normalizarEndereco', () => {
  it('acrescenta a porta padrão quando só vem o IP', () => {
    expect(normalizarEndereco('192.168.3.10')).toBe('192.168.3.10:8765');
    expect(normalizarEndereco('  meu-pc  ')).toBe('meu-pc:8765');
  });

  it('mantém a porta informada', () => {
    expect(normalizarEndereco('192.168.3.10:9000')).toBe('192.168.3.10:9000');
  });

  it('tira o protocolo e o caminho que alguém cole junto', () => {
    expect(normalizarEndereco('http://192.168.3.10:8765/')).toBe('192.168.3.10:8765');
    expect(normalizarEndereco('ws://192.168.3.10/ws')).toBe('192.168.3.10:8765');
  });

  it('texto vazio continua vazio (não troca o endereço)', () => {
    expect(normalizarEndereco('   ')).toBe('');
  });
});
