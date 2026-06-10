import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AppRole, getStoredSession } from '../session';
import { FichaRecepcionPayload, FichasRecepcionService } from '../services/fichas-recepcion.service';

@Component({
  selector: 'app-ficha-recepcion-form-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <main class="shell">
      <section class="header">
        <div>
          <p class="eyebrow">Ficha de Recepcion Vehicular</p>
          <h1>Nueva ficha</h1>
          <p class="subtitle">Registro minimo para recepcion vehicular asociada opcionalmente a una emergencia.</p>
        </div>
        <a class="button ghost" routerLink="/fichas-recepcion">Volver al listado</a>
      </section>

      <section class="card" *ngIf="accessDenied">
        <p class="error">Solo admin y secretaria pueden crear fichas.</p>
      </section>

      <form class="card form-grid" *ngIf="!accessDenied" (ngSubmit)="submit()">
        <div class="grid">
          <label class="field">
            <span>Cliente ID</span>
            <input [(ngModel)]="form.cliente_id" name="cliente_id" type="number" min="1" />
          </label>

          <label class="field">
            <span>Emergencia ID</span>
            <input [(ngModel)]="form.emergencia_id" name="emergencia_id" type="number" min="1" />
          </label>

          <label class="field">
            <span>Vehiculo</span>
            <input [(ngModel)]="form.vehiculo" name="vehiculo" />
          </label>

          <label class="field">
            <span>Placa</span>
            <input [(ngModel)]="form.placa" name="placa" />
          </label>

          <label class="field">
            <span>Marca</span>
            <input [(ngModel)]="form.marca" name="marca" />
          </label>

          <label class="field">
            <span>Modelo</span>
            <input [(ngModel)]="form.modelo" name="modelo" />
          </label>

          <label class="field">
            <span>Ano</span>
            <input [(ngModel)]="form.anio" name="anio" type="number" min="1900" max="2100" />
          </label>

          <label class="field">
            <span>Mecanico asignado ID</span>
            <input [(ngModel)]="form.assigned_mechanic_id" name="assigned_mechanic_id" type="number" min="1" />
          </label>

          <label class="field field-wide">
            <span>Problema reportado</span>
            <textarea [(ngModel)]="form.problema_reportado" name="problema_reportado" required></textarea>
          </label>

          <label class="field field-wide">
            <span>Accesorios recibidos</span>
            <textarea [(ngModel)]="form.accesorios_recibidos" name="accesorios_recibidos"></textarea>
          </label>

          <label class="field field-wide">
            <span>Observaciones</span>
            <textarea [(ngModel)]="form.observaciones" name="observaciones"></textarea>
          </label>
        </div>

        <p *ngIf="isLoading">Guardando ficha...</p>
        <p class="error" *ngIf="errorMessage">{{ errorMessage }}</p>

        <div class="actions">
          <button class="button primary" type="submit" [disabled]="isLoading">Crear ficha</button>
        </div>
      </form>
    </main>
  `,
  styles: [`
    .shell { padding: 2rem; background: #f4f7fb; min-height: 100vh; color: #15304f; }
    .header, .actions { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; }
    .header { margin-bottom: 1.5rem; }
    .eyebrow { margin: 0 0 .35rem; text-transform: uppercase; letter-spacing: .12em; font-size: .78rem; color: #85711b; font-weight: 700; }
    .subtitle { margin: .5rem 0 0; color: #50667f; }
    .card { background: #fff; border-radius: 1.25rem; box-shadow: 0 18px 40px rgba(17, 48, 83, .08); padding: 1.25rem; }
    .form-grid { display: grid; gap: 1rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }
    .field { display: flex; flex-direction: column; gap: .45rem; }
    .field span { font-weight: 600; color: #284c73; }
    .field input, .field textarea { border: 1px solid #c8d5e6; border-radius: .85rem; padding: .8rem .95rem; font: inherit; }
    .field textarea { min-height: 110px; resize: vertical; }
    .field-wide { grid-column: 1 / -1; }
    .button { border: none; border-radius: .85rem; padding: .85rem 1.15rem; text-decoration: none; cursor: pointer; font-weight: 700; font: inherit; }
    .button.primary { background: #10386e; color: #fff; }
    .button.ghost { background: #edf3fa; color: #10386e; }
    .error { color: #b03b2d; }
    @media (max-width: 768px) { .shell { padding: 1rem; } .header, .actions { flex-direction: column; align-items: stretch; } }
  `],
})
export class FichaRecepcionFormPageComponent {
  private readonly service = inject(FichasRecepcionService);
  private readonly router = inject(Router);
  private readonly session = getStoredSession();

  isLoading = false;
  errorMessage = '';

  form: FichaRecepcionPayload = {
    cliente_id: null,
    emergencia_id: null,
    vehiculo: '',
    placa: '',
    marca: '',
    modelo: '',
    anio: null,
    problema_reportado: '',
    accesorios_recibidos: '',
    observaciones: '',
    assigned_mechanic_id: null,
  };

  get role(): AppRole | null {
    return this.session?.role ?? null;
  }

  get accessDenied(): boolean {
    return this.role !== 'admin' && this.role !== 'secretaria';
  }

  submit(): void {
    if (this.accessDenied || this.isLoading) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.service.crear({
      ...this.form,
      vehiculo: this.form.vehiculo?.trim() || null,
      placa: this.form.placa?.trim() || null,
      marca: this.form.marca?.trim() || null,
      modelo: this.form.modelo?.trim() || null,
      problema_reportado: this.form.problema_reportado.trim(),
      accesorios_recibidos: this.form.accesorios_recibidos?.trim() || null,
      observaciones: this.form.observaciones?.trim() || null,
    }).subscribe({
      next: async (detail) => {
        this.isLoading = false;
        await this.router.navigate(['/fichas-recepcion', detail.id]);
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo crear la ficha.';
      },
    });
  }
}
