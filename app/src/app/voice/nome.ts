// Filtro de nome (HANDOFF 5.2): decide se a frase reconhecida chama o Orbit.
// Decisões:
// - Compara por palavra inteira (nunca substring): "exorbitante" não casa.
// - Aceita lista de variantes do STT pt-BR + qualquer palavra de 4 a 7 letras
//   a distância de Levenshtein <= 1 de "orbit". Os negativos pedidos (habit,
//   rabit, robô, orbital, orgulho, bit, ordem, cabide) ficam todos a >= 2,
//   então não foi preciso restringir a regra (ex.: primeira letra).
// - Variantes que o Chrome pt-BR realmente devolveu (vistas no painel "Ouvi:"), mesmo longe de
//   "orbit": "horbit", "hornet". Só entram por evidência: cada uma abre espaço para falso positivo.
// - Palavras adjacentes são juntadas ("or bit" -> "orbit") mas só contra a
//   lista de variantes, sem distância, para evitar falsos positivos tipo "ou bit".
const VARIANTES = new Set(['orbit', 'orbite', 'orbiti', 'orbita', 'obit', 'orbet', 'horbit', 'hornet']);

function levenshtein(a: string, b: string): number {
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    }
    prev = cur;
  }
  return prev[b.length];
}

export function contemOrbit(texto: string): boolean {
  const palavras = texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .split(/[^a-z0-9]+/)
    .filter(Boolean);

  return palavras.some((p, i) => {
    if (VARIANTES.has(p)) return true;
    if (p.length >= 4 && p.length <= 7 && levenshtein(p, 'orbit') <= 1) return true;
    return i + 1 < palavras.length && VARIANTES.has(p + palavras[i + 1]);
  });
}
