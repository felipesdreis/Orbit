import { FalaNavegador } from './fala-navegador';

/** WAV mono 16 bits, 24 kHz, só silêncio (o que importa aqui é a duração). */
function wav(segundos: number): string {
  const amostras = Math.round(24000 * segundos);
  const bytes = new DataView(new ArrayBuffer(44 + amostras * 2));
  const texto = (pos: number, s: string) => [...s].forEach((c, i) => bytes.setUint8(pos + i, c.charCodeAt(0)));
  texto(0, 'RIFF');
  bytes.setUint32(4, 36 + amostras * 2, true);
  texto(8, 'WAVEfmt ');
  bytes.setUint32(16, 16, true);
  bytes.setUint16(20, 1, true);
  bytes.setUint16(22, 1, true);
  bytes.setUint32(24, 24000, true);
  bytes.setUint32(28, 48000, true);
  bytes.setUint16(32, 2, true);
  bytes.setUint16(34, 16, true);
  texto(36, 'data');
  bytes.setUint32(40, amostras * 2, true);
  return URL.createObjectURL(new Blob([bytes.buffer], { type: 'audio/wav' }));
}

describe('FalaNavegador', () => {
  let fala: FalaNavegador;
  let inicios: number[];

  beforeEach(() => {
    fala = new FalaNavegador();
    fala.preparar();
    inicios = [];
    const original = AudioBufferSourceNode.prototype.start;
    spyOn(AudioBufferSourceNode.prototype, 'start').and.callFake(function (this: AudioBufferSourceNode, quando?: number) {
      inicios.push(quando ?? 0);
      return original.call(this, quando);
    });
  });

  afterEach(() => fala.parar());

  it('sem nada na fila, está ociosa', async () => {
    await fala.ociosa();
  });

  it('toca os trechos em ordem, colados um no outro, e só fica ociosa depois do último', async () => {
    fala.enfileirar(wav(0.2));
    fala.enfileirar(wav(0.3));
    const inicio = performance.now();
    await fala.ociosa();
    expect(inicios.length).toBe(2);
    expect(inicios[1] - inicios[0]).toBeCloseTo(0.2, 3); // o 2º começa exatamente quando o 1º termina
    expect(performance.now() - inicio).toBeGreaterThan(400); // esperou os dois tocarem (~0,5 s)
  });

  it('avisa quando o som começa, uma vez por rodada', async () => {
    let avisos = 0;
    fala.aoComecar(() => avisos++);
    fala.enfileirar(wav(0.1));
    fala.enfileirar(wav(0.1));
    await fala.ociosa();
    expect(avisos).toBe(1);
  });

  it('um trecho que falha ao baixar é pulado e não trava a fila', async () => {
    fala.enfileirar('blob:http://localhost/inexistente');
    fala.enfileirar(wav(0.1));
    await fala.ociosa();
    expect(inicios.length).toBe(1);
  });

  it('parar() corta o que toca e libera quem espera', async () => {
    fala.enfileirar(wav(2));
    const espera = fala.ociosa();
    await new Promise((ok) => setTimeout(ok, 100));
    fala.parar();
    await espera; // se parar() não liberasse, o teste estouraria o tempo
    await fala.ociosa();
  });

  it('depois de parar(), uma nova rodada toca normalmente', async () => {
    fala.enfileirar(wav(1));
    fala.parar();
    fala.enfileirar(wav(0.1));
    await fala.ociosa();
    expect(inicios.length).toBe(1);
  });
});
