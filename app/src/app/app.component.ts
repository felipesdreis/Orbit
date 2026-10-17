import { ChangeDetectionStrategy, Component, OnDestroy, signal } from '@angular/core';
import { IonApp, IonButton, IonContent } from '@ionic/angular/standalone';
import { FaceComponent } from './face/face.component';
import { EMOCOES, ESTADOS, Emocao, Estado } from './face/face.types';

@Component({
  selector: 'app-root',
  imports: [IonApp, IonContent, IonButton, FaceComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnDestroy {
  readonly estados = ESTADOS;
  readonly emocoes = EMOCOES;

  estado = signal<Estado>('standby');
  emocao = signal<Emocao>('neutro');
  painel = signal(true);
  demoRodando = signal(false);

  private demoTimers: ReturnType<typeof setTimeout>[] = [];

  ngOnDestroy() {
    this.pararDemo();
  }

  // Roteiro de teste: percorre os estados e as emoções sem precisar clicar.
  demo() {
    if (this.demoRodando()) return this.pararDemo();
    const passos: [number, Estado, Emocao][] = [
      [0, 'standby', 'neutro'],
      [2500, 'ouvindo', 'neutro'],
      [5500, 'pensando', 'neutro'],
      [8000, 'falando', 'feliz'],
      [11000, 'falando', 'curioso'],
      [14000, 'falando', 'surpreso'],
      [17000, 'falando', 'pensando'],
      [20000, 'ouvindo', 'neutro'],
      [23000, 'standby', 'neutro'],
    ];
    this.demoRodando.set(true);
    for (const [quando, estado, emocao] of passos) {
      this.demoTimers.push(setTimeout(() => (this.estado.set(estado), this.emocao.set(emocao)), quando));
    }
    this.demoTimers.push(setTimeout(() => this.demoRodando.set(false), 23500));
  }

  private pararDemo() {
    this.demoTimers.forEach(clearTimeout);
    this.demoTimers = [];
    this.demoRodando.set(false);
  }
}
