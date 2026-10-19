import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.felipereis.orbit',
  appName: 'Orbit',
  webDir: 'dist/app/browser',
  server: {
    // A página é servida em http://localhost (e não https): assim o WebSocket ws://<IP-do-PC>
    // não é bloqueado como conteúdo misto. localhost continua sendo um contexto seguro
    // (microfone, Web Audio e wake lock funcionam).
    androidScheme: 'http',
    cleartext: true,
  },
  android: {
    allowMixedContent: true,
  },
};

export default config;
