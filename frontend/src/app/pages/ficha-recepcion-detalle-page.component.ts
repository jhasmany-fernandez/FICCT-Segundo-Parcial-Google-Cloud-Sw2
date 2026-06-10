import { CommonModule, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AppRole, getStoredSession } from '../session';
import { FichaRecepcionDetail, FichasRecepcionService } from '../services/fichas-recepcion.service';

@Component({
  selector: 'app-ficha-recepcion-detalle-page',
  standalone: true,
  imports: [CommonModule, RouterLink, DatePipe],
  template: `
    <main class="shell">
      <section class="header">
        <div>
          <p class="eyebrow">Ficha de Recepcion Vehicular</p>
          <h1>Detalle de ficha</h1>
        </div>
        <a class="button ghost" routerLink="/fichas-recepcion">Volver al listado</a>
      </section>

      <section class="card" *ngIf="accessDenied">
        <p class="error">Solo admin y secretaria pueden ver el detalle de fichas.</p>
      </section>

      <section class="card" *ngIf="!accessDenied && isLoading">
        <p>Cargando detalle...</p>
      </section>

      <section class="card" *ngIf="!accessDenied && !isLoading && errorMessage">
        <p class="error">{{ errorMessage }}</p>
      </section>

      <section class="card" *ngIf="!accessDenied && !isLoading && detail">
        <ul class="detail-list">
          <li><strong>Codigo:</strong> {{ detail.codigo_ficha }}</li>
          <li><strong>Estado:</strong> {{ detail.estado }}</li>
          <li><strong>Cliente ID:</strong> {{ detail.cliente_id ?? '-' }}</li>
          <li><strong>Emergencia ID:</strong> {{ detail.emergencia_id ?? '-' }}</li>
          <li><strong>Recibido por:</strong> {{ detail.recibido_por_id ?? '-' }}</li>
          <li><strong>Vehiculo:</strong> {{ detail.vehiculo }}</li>
          <li><strong>Placa:</strong> {{ detail.placa || '-' }}</li>
          <li><strong>Marca:</strong> {{ detail.marca || '-' }}</li>
          <li><strong>Modelo:</strong> {{ detail.modelo || '-' }}</li>
          <li><strong>Ano:</strong> {{ detail.anio ?? '-' }}</li>
          <li><strong>Problema reportado:</strong> {{ detail.problema_reportado }}</li>
          <li><strong>Accesorios recibidos:</strong> {{ detail.accesorios_recibidos || 'Sin registro' }}</li>
          <li><strong>Observaciones:</strong> {{ detail.observaciones || 'Sin observaciones' }}</li>
          <li><strong>Mecanico asignado:</strong> {{ detail.assigned_mechanic_name || detail.assigned_mechanic_id || 'Sin asignar' }}</li>
          <li><strong>Fecha de ingreso:</strong> {{ detail.fecha_ingreso | date:'short' }}</li>
        </ul>
      </section>
    </main>
  `,
  styles: [`
    .shell { padding: 2rem; background: #f4f7fb; min-height: 100vh; color: #15304f; }
    .header { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; margin-bottom: 1.5rem; }
    .eyebrow { margin: 0 0 .35rem; text-transform: uppercase; letter-spacing: .12em; font-size: .78rem; color: #85711b; font-weight: 700; }
    .card { background: #fff; border-radius: 1.25rem; box-shadow: 0 18px 40px rgba(17, 48, 83, .08); padding: 1.25rem; }
    .detail-list { list-style: none; padding: 0; margin: 0; display: grid; gap: .7rem; }
    .button { border: none; border-radius: .85rem; padding: .85rem 1.15rem; text-decoration: none; cursor: pointer; font-weight: 700; font: inherit; }
    .button.ghost { background: #edf3fa; color: #10386e; }
    .error { color: #b03b2d; }
    @media (max-width: 768px) { .shell { padding: 1rem; } .header { flex-direction: column; align-items: stretch; } }
  `],
})
export class FichaRecepcionDetallePageComponent implements OnInit {
  private readonly service = inject(FichasRecepcionService);
  private readonly route = inject(ActivatedRoute);
  private readonly session = getStoredSession();

  detail: FichaRecepcionDetail | null = null;
  isLoading = false;
  errorMessage = '';

  get role(): AppRole | null {
    return this.session?.role ?? null;
  }

  get accessDenied(): boolean {
    return this.role !== 'admin' && this.role !== 'secretaria';
  }

  ngOnInit(): void {
    if (this.accessDenied) {
      return;
    }

    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) {
      this.errorMessage = 'No se encontro la ficha solicitada.';
      return;
    }

    this.isLoading = true;
    this.service.obtener(id).subscribe({
      next: (detail) => {
        this.detail = detail;
        this.isLoading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo cargar el detalle.';
      },
    });
  }
}
