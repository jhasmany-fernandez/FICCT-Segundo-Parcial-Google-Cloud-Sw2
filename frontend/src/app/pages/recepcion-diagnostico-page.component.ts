import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { getStoredSession } from '../session';
import { RecepcionesService } from '../services/recepciones.service';

@Component({
  selector: 'app-recepcion-diagnostico-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <main class="simple-shell">
      <section class="header">
        <div>
          <p class="eyebrow">Recepción de Vehículos</p>
          <h1>Registrar diagnóstico mecánico</h1>
        </div>
        <a class="button ghost" [routerLink]="['/recepciones', recepcionId]">Volver al detalle</a>
      </section>

      <section class="card" *ngIf="accessDenied">
        <p class="error">Solo el rol mecánico puede registrar diagnósticos.</p>
      </section>

      <form class="card form-grid" *ngIf="!accessDenied" (ngSubmit)="submit()">
        <label class="field">
          <span>Diagnóstico mecánico</span>
          <textarea [(ngModel)]="form.diagnostic_text" name="diagnostic_text" required></textarea>
        </label>

        <label class="field">
          <span>Trabajo estimado</span>
          <textarea [(ngModel)]="form.estimated_work" name="estimated_work"></textarea>
        </label>

        <label class="field">
          <span>Costo estimado</span>
          <input [(ngModel)]="form.estimated_cost" name="estimated_cost" type="number" min="0" step="0.01" />
        </label>

        <p class="loading" *ngIf="isLoading">Registrando diagnóstico...</p>
        <p class="error" *ngIf="errorMessage">{{ errorMessage }}</p>

        <div class="actions">
          <button class="button primary" type="submit" [disabled]="isLoading">Guardar diagnóstico</button>
        </div>
      </form>
    </main>
  `,
  styles: [`
    .simple-shell { min-height: 100vh; background: #f4f7fb; padding: 2rem; color: #15304f; }
    .header, .actions { display: flex; justify-content: space-between; gap: 1rem; align-items: center; margin-bottom: 1rem; }
    .eyebrow { margin: 0 0 .35rem; text-transform: uppercase; letter-spacing: .12em; font-size: .78rem; color: #85711b; font-weight: 700; }
    .card { background: #fff; border-radius: 1.25rem; box-shadow: 0 18px 40px rgba(17, 48, 83, .08); padding: 1.25rem; }
    .form-grid { display: grid; gap: 1rem; }
    .field { display: flex; flex-direction: column; gap: .45rem; }
    .field span { font-weight: 600; color: #284c73; }
    .field input, .field textarea { border: 1px solid #c8d5e6; border-radius: .85rem; padding: .8rem .95rem; font: inherit; }
    .field textarea { min-height: 120px; resize: vertical; }
    .button { border: none; border-radius: .85rem; padding: .85rem 1.15rem; text-decoration: none; cursor: pointer; font-weight: 700; font: inherit; }
    .button.primary { background: #10386e; color: #fff; }
    .button.ghost { background: #edf3fa; color: #10386e; }
    .error { color: #b03b2d; }
    @media (max-width: 768px) { .simple-shell { padding: 1rem; } .header, .actions { flex-direction: column; align-items: stretch; } }
  `],
})
export class RecepcionDiagnosticoPageComponent {
  private readonly recepcionesService = inject(RecepcionesService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly session = getStoredSession();

  readonly recepcionId = Number(this.route.snapshot.paramMap.get('id'));
  accessDenied = this.session?.role !== 'mecanico';
  isLoading = false;
  errorMessage = '';

  form = {
    diagnostic_text: '',
    estimated_work: '',
    estimated_cost: null as number | null,
  };

  submit(): void {
    if (this.accessDenied || this.isLoading || !this.recepcionId) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.recepcionesService
      .crearDiagnostico(this.recepcionId, {
        diagnostic_text: this.form.diagnostic_text.trim(),
        estimated_work: this.form.estimated_work.trim() || null,
        estimated_cost: this.form.estimated_cost,
      })
      .subscribe({
        next: async () => {
          this.isLoading = false;
          await this.router.navigate(['/recepciones', this.recepcionId]);
        },
        error: (error: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = this.resolveErrorMessage(error);
        },
      });
  }

  private resolveErrorMessage(error: HttpErrorResponse): string {
    const detail = error.error?.detail;

    if (error.status === 403) {
      return 'No tienes permisos para registrar diagnósticos.';
    }

    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }

    if (error.status === 422 || error.status === 400) {
      return 'Revisa el formulario antes de continuar.';
    }

    return 'No se pudo guardar el diagnóstico.';
  }
}
