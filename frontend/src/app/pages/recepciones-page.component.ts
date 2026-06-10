import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { AppRole, getStoredSession } from '../session';
import { RecepcionListItem, RecepcionListResponse, RecepcionesService, RecepcionStatus } from '../services/recepciones.service';

@Component({
  selector: 'app-recepciones-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DatePipe],
  template: `
    <main class="recepciones-shell">
      <section class="recepciones-header">
        <div>
          <p class="eyebrow">Recepción de Vehículos</p>
          <h1>Recepciones registradas</h1>
          <p class="subtitle">Consulta, filtra y gestiona las fichas de recepción desde el panel web.</p>
        </div>

        <div class="header-actions">
          <a class="button ghost" routerLink="/dashboard">Volver al dashboard</a>
          <a class="button primary" routerLink="/recepciones/nueva" *ngIf="canCreateRecepcion">Nueva recepción</a>
        </div>
      </section>

      <section class="recepciones-card filters-card">
        <div class="filters-grid">
          <label class="field">
            <span>Estado</span>
            <select [(ngModel)]="filters.status">
              <option value="">Todos</option>
              <option *ngFor="let option of statusOptions" [value]="option">{{ option }}</option>
            </select>
          </label>

          <label class="field">
            <span>Placa</span>
            <input type="text" [(ngModel)]="filters.plate" placeholder="1234ABC" />
          </label>

          <label class="field">
            <span>Código ficha</span>
            <input type="text" [(ngModel)]="filters.codigo_ficha" placeholder="REC-2026..." />
          </label>

          <label class="field">
            <span>Carnet</span>
            <input type="text" [(ngModel)]="filters.identity_card" placeholder="1234567" />
          </label>
        </div>

        <div class="filters-actions">
          <button class="button primary" type="button" (click)="applyFilters()" [disabled]="isLoading">Buscar</button>
          <button class="button ghost" type="button" (click)="resetFilters()" [disabled]="isLoading">Limpiar</button>
        </div>
      </section>

      <section class="recepciones-card">
        <div class="toolbar">
          <div>
            <strong>Total:</strong> {{ total }}
            <span class="toolbar-detail">Mostrando {{ recepciones.length }} registros</span>
          </div>

          <div class="pagination">
            <button class="button ghost" type="button" (click)="goPrevious()" [disabled]="offset === 0 || isLoading">
              Anterior
            </button>
            <button
              class="button ghost"
              type="button"
              (click)="goNext()"
              [disabled]="offset + limit >= total || isLoading"
            >
              Siguiente
            </button>
          </div>
        </div>

        <p class="loading" *ngIf="isLoading">Cargando recepciones...</p>
        <p class="error" *ngIf="!isLoading && errorMessage">{{ errorMessage }}</p>
        <p class="empty" *ngIf="!isLoading && !errorMessage && !recepciones.length">
          No hay recepciones para los filtros seleccionados.
        </p>

        <div class="table-wrap" *ngIf="!isLoading && recepciones.length">
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>Cliente</th>
                <th>Placa</th>
                <th>Vehículo</th>
                <th>Estado</th>
                <th>Recepción</th>
                <th>Mecánico</th>
                <th>Acciones</th>
              </tr>
            </thead>

            <tbody>
              <tr *ngFor="let item of recepciones">
                <td>{{ item.codigo_ficha }}</td>
                <td>{{ item.client_full_name }}</td>
                <td>{{ item.plate }}</td>
                <td>{{ item.vehicle_label }}</td>
                <td><span class="status-pill">{{ item.status }}</span></td>
                <td>{{ item.fecha_recepcion | date:'short' }}</td>
                <td>{{ item.assigned_mecanico_name || 'Sin asignar' }}</td>
                <td class="actions-cell">
                  <a class="inline-link" [routerLink]="['/recepciones', item.id]">Ver detalle</a>
                  <a class="inline-link" [routerLink]="['/recepciones', item.id, 'editar']" *ngIf="canEditRecepcion">
                    Editar
                  </a>
                  <a
                    class="inline-link"
                    [routerLink]="['/recepciones', item.id, 'diagnostico']"
                    *ngIf="canRegisterDiagnostico"
                  >
                    Diagnóstico
                  </a>
                  <a
                    class="inline-link"
                    [routerLink]="['/recepciones', item.id, 'observaciones']"
                    *ngIf="canRegisterObservacion"
                  >
                    Observación
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  `,
  styles: [`
    .recepciones-shell { padding: 2rem; background: #f4f7fb; min-height: 100vh; color: #15304f; }
    .recepciones-header { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; margin-bottom: 1.5rem; }
    .eyebrow { margin: 0 0 .35rem; text-transform: uppercase; letter-spacing: .12em; font-size: .78rem; color: #85711b; font-weight: 700; }
    h1 { margin: 0; font-size: 2rem; }
    .subtitle { margin: .5rem 0 0; max-width: 46rem; color: #4b617d; }
    .header-actions, .filters-actions, .pagination { display: flex; gap: .75rem; flex-wrap: wrap; }
    .recepciones-card { background: #fff; border-radius: 1.25rem; box-shadow: 0 18px 40px rgba(17, 48, 83, .08); padding: 1.25rem; margin-bottom: 1.25rem; }
    .filters-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
    .field { display: flex; flex-direction: column; gap: .45rem; font-size: .92rem; }
    .field span { font-weight: 600; color: #284c73; }
    .field input, .field select { border: 1px solid #c8d5e6; border-radius: .85rem; padding: .8rem .95rem; font: inherit; }
    .filters-actions { margin-top: 1rem; }
    .button { border: none; border-radius: .85rem; padding: .85rem 1.15rem; text-decoration: none; cursor: pointer; font-weight: 700; font: inherit; }
    .button.primary { background: #10386e; color: #fff; }
    .button.ghost { background: #edf3fa; color: #10386e; }
    .toolbar { display: flex; justify-content: space-between; gap: 1rem; align-items: center; margin-bottom: 1rem; }
    .toolbar-detail { margin-left: .5rem; color: #60758f; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 980px; }
    th, td { text-align: left; padding: .9rem .85rem; border-bottom: 1px solid #e3ebf4; vertical-align: top; }
    th { color: #48617f; font-size: .82rem; text-transform: uppercase; letter-spacing: .06em; }
    .status-pill { display: inline-flex; padding: .35rem .7rem; background: #eef5ff; color: #0c4b86; border-radius: 999px; font-size: .85rem; font-weight: 700; }
    .actions-cell { display: flex; flex-direction: column; gap: .35rem; }
    .inline-link { color: #10386e; font-weight: 600; text-decoration: none; }
    .loading, .empty, .error { margin: 1rem 0 0; }
    .error { color: #b03b2d; }
    @media (max-width: 768px) {
      .recepciones-shell { padding: 1rem; }
      .recepciones-header, .toolbar { flex-direction: column; align-items: stretch; }
    }
  `],
})
export class RecepcionesPageComponent implements OnInit {
  private readonly recepcionesService = inject(RecepcionesService);
  private readonly session = getStoredSession();

  readonly statusOptions: RecepcionStatus[] = [
    'registrada',
    'en_diagnostico',
    'en_trabajo',
    'finalizada',
    'entregada',
  ];

  readonly limit = 20;
  recepciones: RecepcionListItem[] = [];
  total = 0;
  offset = 0;
  isLoading = false;
  errorMessage = '';
  filters = {
    status: '',
    plate: '',
    codigo_ficha: '',
    identity_card: '',
  };

  get role(): AppRole | null {
    return this.session?.role ?? null;
  }

  get canCreateRecepcion(): boolean {
    return this.role === 'secretaria';
  }

  get canEditRecepcion(): boolean {
    return this.role === 'secretaria' || this.role === 'admin';
  }

  get canRegisterDiagnostico(): boolean {
    return this.role === 'mecanico';
  }

  get canRegisterObservacion(): boolean {
    return this.role === 'mecanico';
  }

  ngOnInit(): void {
    this.loadRecepciones();
  }

  applyFilters(): void {
    this.offset = 0;
    this.loadRecepciones();
  }

  resetFilters(): void {
    this.filters = {
      status: '',
      plate: '',
      codigo_ficha: '',
      identity_card: '',
    };
    this.offset = 0;
    this.loadRecepciones();
  }

  goPrevious(): void {
    this.offset = Math.max(0, this.offset - this.limit);
    this.loadRecepciones();
  }

  goNext(): void {
    this.offset += this.limit;
    this.loadRecepciones();
  }

  private loadRecepciones(): void {
    this.isLoading = true;
    this.errorMessage = '';

    this.recepcionesService
      .listarRecepciones({
        ...this.filters,
        limit: this.limit,
        offset: this.offset,
      })
      .subscribe({
        next: (response: RecepcionListResponse) => {
          this.recepciones = response.items;
          this.total = response.total;
          this.offset = response.offset;
          this.isLoading = false;
        },
        error: (error: HttpErrorResponse) => {
          this.recepciones = [];
          this.total = 0;
          this.isLoading = false;
          this.errorMessage = this.resolveErrorMessage(error);
        },
      });
  }

  private resolveErrorMessage(error: HttpErrorResponse): string {
    const detail = error.error?.detail;

    if (error.status === 403) {
      return 'No tienes permisos para consultar recepciones.';
    }

    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }

    return 'No se pudo cargar el listado de recepciones.';
  }
}
