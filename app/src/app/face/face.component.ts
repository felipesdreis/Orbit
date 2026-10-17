import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, input, signal } from '@angular/core';
import { Emocao, Estado } from './face.types';

@Component({
  selector: 'app-face',
  templateUrl: './face.component.html',
  styleUrl: './face.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FaceComponent implements OnInit, OnDestroy {
  estado = input<Estado>('standby');
  emocao = input<Emocao>('neutro');

  // Em standby e pensando o estado manda; nos demais vale a emoção.
  visual = computed(() => {
    const estado = this.estado();
    return estado === 'standby' || estado === 'pensando' ? estado : this.emocao();
  });

  piscando = signal(false);
  olhar = signal({ x: 0, y: 0 });

  private timers = new Set<ReturnType<typeof setTimeout>>();
  private vivo = true;

  ngOnInit() {
    this.agendar(() => this.piscar(), 2500, 6000);
    this.agendar(() => this.moverOlhar(), 3000, 7000);
  }

  ngOnDestroy() {
    this.vivo = false;
    this.timers.forEach(clearTimeout);
  }

  private agendar(acao: () => void, min: number, max: number) {
    if (!this.vivo) return;
    const t = setTimeout(() => {
      this.timers.delete(t);
      acao();
      this.agendar(acao, min, max);
    }, min + Math.random() * (max - min));
    this.timers.add(t);
  }

  private piscar() {
    if (this.estado() === 'standby') return;
    this.piscando.set(true);
    const t = setTimeout(() => {
      this.timers.delete(t);
      this.piscando.set(false);
    }, 140);
    this.timers.add(t);
  }

  private moverOlhar() {
    const parado = this.estado() === 'standby' || this.estado() === 'pensando';
    this.olhar.set(parado || Math.random() < 0.4 ? { x: 0, y: 0 } : { x: (Math.random() - 0.5) * 24, y: (Math.random() - 0.5) * 12 });
  }
}
