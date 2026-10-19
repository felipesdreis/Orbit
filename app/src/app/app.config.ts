import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideIonicAngular } from '@ionic/angular/standalone';
import { Api } from './api/api';
import { ApiWebSocket } from './api/api-websocket';
import { Fala } from './voice/fala';
import { FalaNavegador } from './voice/fala-navegador';
import { Stt } from './voice/stt';
import { SttWebSpeech } from './voice/stt-webspeech';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideIonicAngular({ mode: 'md' }),
    // Implementações reais; os testes trocam por falsas. No APK (etapa 4) o Stt vira o plugin nativo.
    { provide: Api, useClass: ApiWebSocket },
    { provide: Stt, useClass: SttWebSpeech },
    { provide: Fala, useClass: FalaNavegador },
  ],
};
