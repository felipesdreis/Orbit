import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { provideIonicAngular } from '@ionic/angular/standalone';
import { Api } from './api/api';
import { ApiWebSocket } from './api/api-websocket';
import { Fala } from './voice/fala';
import { FalaNavegador } from './voice/fala-navegador';
import { Stt } from './voice/stt';
import { SttNativo } from './voice/stt-nativo';
import { SttWebSpeech } from './voice/stt-webspeech';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideIonicAngular({ mode: 'md' }),
    // Implementações reais; os testes trocam por falsas. No APK o reconhecimento é o nativo do Android.
    { provide: Api, useClass: ApiWebSocket },
    { provide: Stt, useClass: Capacitor.isNativePlatform() ? SttNativo : SttWebSpeech },
    { provide: Fala, useClass: FalaNavegador },
  ],
};
