import { contemOrbit } from './nome';

describe('contemOrbit', () => {
  const positivos = [
    'orbit', 'Orbit', 'ORBIT!', 'ei orbit', 'orbit, que horas são',
    'que horas são, orbit?', 'olá Órbita', 'orbite', 'orbiti', 'obit', 'orbet',
    'horbit', 'hornet', 'Hornet, que horas são?', 'ei hornet', 'or bit', 'Ór bit, tudo bem?', 'ei or bit que horas são',
    'fala com o orbit agora', 'orbits', 'arbit',
  ];
  const negativos = [
    'exorbitante', 'habit', 'rabit', 'robô', 'orbital', 'orgulho', 'bit',
    'ordem', 'cabide', 'horn', 'hornets', 'honest', '', '   ', 'que horas são', 'ou bit',
  ];

  positivos.forEach((t) =>
    it(`casa: "${t}"`, () => expect(contemOrbit(t)).toBeTrue()));
  negativos.forEach((t) =>
    it(`não casa: "${t}"`, () => expect(contemOrbit(t)).toBeFalse()));
});
