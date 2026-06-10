import { CommonModule, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AppRole, getStoredSession } from '../session';
import { FichaRecepcionListItem, FichasRecepcionService } from '../services/fichas-recepcion.service';

@Component({
  selector: 'app-fichas-recepcion-page',
  standalone: true,
  imports: [CommonModule, RouterLink, DatePipe],
  template: `
    <main class="shell">
      <section class="header">
        <div>
          <p class="eyebrow">Ficha de Recepcion Vehicular</p>
          <h1>Fichas de recepcion</h1>
          <p class="subtitle">Consulta y registra fichas basicas para conectar el dashboard con el flujo movil del mecanico.</p>
        </div>
        <div class="actions">
          <a class="button ghost" routerLink="/dashboard">Volver al dashboard</a>
          <a class="button primary" routerLink="/fichas-recepcion/nueva" *ngIf="canCreate">Nueva ficha</a>
        </div>
      </section>

      <section class="card" *ngIf="accessDenied">
        <p class="error">Solo admin y secretaria pueden consultar fichas de recepcion.</p>
      </section>

      <section class="card" *ngIf="!accessDenied">
        <p *ngIf="isLoading">Cargando fichas...</p>
        <p class="error" *ngIf="!isLoading && errorMessage">{{ errorMessage }}</p>
        <p class="empty" *ngIf="!isLoading && !errorMessage && !items.length">No hay fichas registradas.</p>

        <div class="table-wrap" *ngIf="!isLoading && items.length">
          <table>
            <thead>
              <tr>
                <th>Codigo</th>
                <th>Emergencia</th>
                <th>Cliente</th>
                <th>Vehiculo</th>
                <th>Placa</th>
                <th>Problema</th>
                <th>Mecanico</th>
                <th>Ingreso</th>
                <th>Estado</th>
                <th>Accion</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let item of items">
                <td>{{ item.codigo_ficha }}</td>
                <td>{{ item.emergencia_id ?? '-' }}</td>
                <td>{{ item.cliente_id ?? '-' }}</td>
                <td>{{ item.vehiculo }}</td>
                <td>{{ item.placa || '-' }}</td>
                <td>{{ item.problema_reportado }}</td>
                <td>{{ item.assigned_mechanic_name || item.assigned_mechanic_id || 'Sin asignar' }}</td>
                <td>{{ item.fecha_ingreso | date:'short' }}</td>
                <td><span class="pill">{{ item.estado }}</span></td>
                <td><a class="link" [routerLink]="['/fichas-recepcion', item.id]">Ver detalle</a></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  `,
  styles: [`
    .shell { padding: 2rem; background: #f4f7fb; min-height: 100vh; color: #15304f; }
    .header, .actions { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; }
    .header { margin-bottom: 1.5rem; }
    .eyebrow { margin: 0 0 .35rem; text-transform: uppercase; letter-spacing: .12em; font-size: .78rem; color: #85711b; font-weight: 700; }
    .subtitle { margin: .5rem 0 0; color: #50667f; max-width: 48rem; }
    .card { background: #fff; border-radius: 1.25rem; box-shadow: 0 18px 40px rgba(17, 48, 83, .08); padding: 1.25rem; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 1080px; }
    th, td { text-align: left; padding: .85rem; border-bottom: 1px solid #e3ebf4; vertical-align: top; }
    th { text-transform: uppercase; font-size: .8rem; color: #48617f; }
    .button { border: none; border-radius: .85rem; padding: .85rem 1.15rem; text-decoration: none; cursor: pointer; font-weight: 700; font: inherit; }
    .button.primary { background: #10386e; color: #fff; }
    .button.ghost { background: #edf3fa; color: #10386e; }
    .pill { display: inline-flex; padding: .35rem .7rem; background: #eef5ff; color: #0c4b86; border-radius: 999px; font-size: .85rem; font-weight: 700; }
    .link { color: #10386e; font-weight: 600; text-decoration: none; }
    .error { color: #b03b2d; }
    .empty { color: #60758f; }
    @media (max-width: 768px) { .shell { padding: 1rem; } .header, .actions { flex-direction: column; align-items: stretch; } }
  `],
})
export class FichasRecepcionPageComponent implements OnInit {
  private readonly service = inject(FichasRecepcionService);
  private readonly session = getStoredSession();

  items: FichaRecepcionListItem[] = [];
  isLoading = false;
  errorMessage = '';

  get role(): AppRole | null {
    return this.session?.role ?? null;
  }

  get accessDenied(): boolean {
    return this.role !== 'admin' && this.role !== 'secretaria';
  }

  get canCreate(): boolean {
    return !this.accessDenied;
  }

  ngOnInit(): void {
    if (this.accessDenied) {
      return;
    }
    this.isLoading = true;
    this.service.listar().subscribe({
      next: (items) => {
        this.items = items;
        this.isLoading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo cargar el listado.';
      },
    });
  }
}
