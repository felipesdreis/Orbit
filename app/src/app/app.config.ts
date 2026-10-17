import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideIonicAngular } from '@ionic/angular/standalone';

export const appConfig: ApplicationConfig = {
  providers: [provideZoneChangeDetection({ eventCoalescing: true }), provideIonicAngular({ mode: 'md' })]
};
