import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, inject, signal, viewChild } from '@angular/core';
import { IonApp, IonButton, IonContent } from '@ionic/angular/standalone';
import { Api } from './api/api';
import { FaceComponent } from './face/face.component';
import { EMOCOES, ESTADOS, Emocao, Estado } from './face/face.types';
import { AtivadorToque } from './voice/ativador';
import { OrbitService } from './voice/orbit.service';

@Component({
  selector: 'app-root',
  imports: [IonApp, IonContent, IonButton, FaceComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements AfterViewInit, OnDestroy {
  readonly orbit = inject(OrbitService);
  readonly api = inject(Api);
  readonly estados = ESTADOS;
  readonly emocoes = EMOCOES;

  private palco = viewChild.required<ElementRef<HTMLElement>>('palco');

  painel = signal(true);
  demoRodando = signal(false);

  private demoTimers: ReturnType<typeof setTimeout>[] = [];

  ngAfterViewInit() {
    // O toque só acorda na área da carinha, para os botões do painel não ligarem o microfone.
    new AtivadorToque(this.palco().nativeElement).onAcordar(() => this.orbit.acordar());
  }

  ngOnDestroy() {
    this.pararDemo();
  }

  conectarA(endereco: string) {
    this.api.definirServidor(endereco);
  }

  // Os botões do painel só mexem na aparência; a conversa real continua pelo OrbitService.
  forcar(estado: Estado) {
    this.orbit.estado.set(estado);
  }

  forcarEmocao(emocao: Emocao) {
    this.orbit.emocao.set(emocao);
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
      this.demoTimers.push(setTimeout(() => (this.forcar(estado), this.forcarEmocao(emocao)), quando));
    }
    this.demoTimers.push(setTimeout(() => this.demoRodando.set(false), 23500));
  }

  private pararDemo() {
    this.demoTimers.forEach(clearTimeout);
    this.demoTimers = [];
    this.demoRodando.set(false);
  }
}
