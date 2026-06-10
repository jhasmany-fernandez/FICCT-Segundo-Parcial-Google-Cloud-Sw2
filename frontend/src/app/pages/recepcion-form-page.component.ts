import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AppRole, getStoredSession } from '../session';
import {
  FuelLevel,
  ProblemaPriority,
  ProblemaReportedBy,
  RecepcionMechanicOption,
  RecepcionesService,
  RecepcionStatus,
  RecepcionPayload,
} from '../services/recepciones.service';

type AccesorioForm = {
  name: string;
  quantity: number;
  notes: string;
};

type ProblemaForm = {
  description: string;
  priority: ProblemaPriority | '';
  reported_by: ProblemaReportedBy;
};

@Component({
  selector: 'app-recepcion-form-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <main class="recepcion-form-shell">
      <section class="header">
        <div>
          <p class="eyebrow">Recepción de Vehículos</p>
          <h1>{{ isEditMode ? 'Editar recepción' : 'Nueva recepción' }}</h1>
          <p class="subtitle">
            Registra la ficha completa del cliente, vehículo, accesorios y problemas reportados.
          </p>
        </div>

        <div class="header-actions">
          <a class="button ghost" routerLink="/recepciones">Volver al listado</a>
        </div>
      </section>

      <section class="card" *ngIf="accessDenied">
        <p class="error">No tienes permisos para {{ isEditMode ? 'editar' : 'crear' }} recepciones.</p>
      </section>

      <form class="form-grid" *ngIf="!accessDenied" (ngSubmit)="submitForm()">
        <section class="card">
          <h2>Cliente</h2>
          <div class="grid">
            <label class="field">
              <span>Nombre completo</span>
              <input [(ngModel)]="form.cliente.full_name" name="full_name" required />
            </label>

            <label class="field">
              <span>Carnet</span>
              <input [(ngModel)]="form.cliente.identity_card" name="identity_card" required />
            </label>

            <label class="field">
              <span>Teléfono</span>
              <input [(ngModel)]="form.cliente.phone" name="phone" required />
            </label>

            <label class="field">
              <span>Email</span>
              <input [(ngModel)]="form.cliente.email" name="email" type="email" />
            </label>

            <label class="field field-wide">
              <span>Dirección</span>
              <input [(ngModel)]="form.cliente.address" name="address" />
            </label>

            <label class="field">
              <span>ID cliente móvil</span>
              <input [(ngModel)]="form.cliente.mobile_client_id" name="mobile_client_id" type="number" min="1" />
            </label>
          </div>
        </section>

        <section class="card">
          <h2>Vehículo</h2>
          <div class="grid">
            <label class="field">
              <span>Placa</span>
              <input [(ngModel)]="form.vehiculo.plate" name="plate" required />
            </label>

            <label class="field">
              <span>Marca</span>
              <input [(ngModel)]="form.vehiculo.brand" name="brand" required />
            </label>

            <label class="field">
              <span>Modelo</span>
              <input [(ngModel)]="form.vehiculo.model" name="model" required />
            </label>

            <label class="field">
              <span>Año</span>
              <input [(ngModel)]="form.vehiculo.year" name="year" type="number" min="1900" max="2100" required />
            </label>

            <label class="field">
              <span>Color</span>
              <input [(ngModel)]="form.vehiculo.color" name="color" required />
            </label>

            <label class="field">
              <span>VIN</span>
              <input [(ngModel)]="form.vehiculo.vin" name="vin" />
            </label>

            <label class="field">
              <span>Número de motor</span>
              <input [(ngModel)]="form.vehiculo.engine_number" name="engine_number" />
            </label>
          </div>
        </section>

        <section class="card">
          <h2>Ficha</h2>
          <div class="grid">
            <label class="field">
              <span>Kilometraje</span>
              <input [(ngModel)]="form.ficha.kilometraje" name="kilometraje" type="number" min="0" />
            </label>

            <label class="field">
              <span>Nivel de combustible</span>
              <select [(ngModel)]="form.ficha.nivel_combustible" name="nivel_combustible">
                <option value="">Seleccionar</option>
                <option *ngFor="let option of fuelLevels" [value]="option">{{ option }}</option>
              </select>
            </label>

            <label class="field">
              <span>Mecánico asignado</span>
              <select
                [(ngModel)]="form.ficha.assigned_mecanico_id"
                name="assigned_mecanico_id"
                [disabled]="isLoadingMechanics"
              >
                <option [ngValue]="null">
                  {{ isLoadingMechanics ? 'Cargando mecánicos...' : 'Sin asignar' }}
                </option>
                <option *ngFor="let mechanic of availableMechanics" [ngValue]="mechanic.id">
                  {{ formatMechanicOption(mechanic) }}
                </option>
              </select>
            </label>

            <p class="field-hint field-wide" *ngIf="!isLoadingMechanics && !availableMechanics.length">
              No hay usuarios con rol mecánico activos disponibles para asignar.
            </p>

            <p class="field-hint field-wide" *ngIf="form.ficha.assigned_mecanico_id">
              Se asignará el usuario mecánico #{{ form.ficha.assigned_mecanico_id }} para diagnóstico y seguimiento.
            </p>

            <label class="field" *ngIf="isEditMode">
              <span>Estado</span>
              <select [(ngModel)]="form.ficha.status" name="status">
                <option *ngFor="let option of statusOptions" [value]="option">{{ option }}</option>
              </select>
            </label>

            <label class="field field-wide">
              <span>Observaciones generales</span>
              <textarea [(ngModel)]="form.ficha.observaciones_generales" name="observaciones_generales"></textarea>
            </label>
          </div>
        </section>

        <section class="card">
          <div class="section-head">
            <h2>Accesorios</h2>
            <button class="button ghost" type="button" (click)="addAccesorio()">Agregar accesorio</button>
          </div>

          <div class="repeat-card" *ngFor="let accesorio of accesorios; let index = index">
            <div class="grid">
              <label class="field">
                <span>Nombre</span>
                <input [(ngModel)]="accesorio.name" [name]="'accesorio_name_' + index" />
              </label>

              <label class="field">
                <span>Cantidad</span>
                <input [(ngModel)]="accesorio.quantity" [name]="'accesorio_quantity_' + index" type="number" min="1" />
              </label>

              <label class="field field-wide">
                <span>Notas</span>
                <input [(ngModel)]="accesorio.notes" [name]="'accesorio_notes_' + index" />
              </label>
            </div>

            <button class="inline-danger" type="button" (click)="removeAccesorio(index)">Quitar</button>
          </div>
        </section>

        <section class="card">
          <div class="section-head">
            <h2>Problemas reportados</h2>
            <button class="button ghost" type="button" (click)="addProblema()">Agregar problema</button>
          </div>

          <div class="repeat-card" *ngFor="let problema of problemas; let index = index">
            <div class="grid">
              <label class="field field-wide">
                <span>Descripción</span>
                <textarea [(ngModel)]="problema.description" [name]="'problema_description_' + index"></textarea>
              </label>

              <label class="field">
                <span>Prioridad</span>
                <select [(ngModel)]="problema.priority" [name]="'problema_priority_' + index">
                  <option value="">Seleccionar</option>
                  <option *ngFor="let option of priorityOptions" [value]="option">{{ option }}</option>
                </select>
              </label>

              <label class="field">
                <span>Reportado por</span>
                <select [(ngModel)]="problema.reported_by" [name]="'problema_reported_by_' + index">
                  <option value="secretaria">secretaria</option>
                  <option value="cliente">cliente</option>
                </select>
              </label>
            </div>

            <button class="inline-danger" type="button" (click)="removeProblema(index)">Quitar</button>
          </div>
        </section>

        <section class="card">
          <p class="loading" *ngIf="isLoading">{{ isEditMode ? 'Actualizando recepción...' : 'Creando recepción...' }}</p>
          <p class="error" *ngIf="errorMessage">{{ errorMessage }}</p>

          <div class="submit-row">
            <button class="button primary" type="submit" [disabled]="isLoading">
              {{ isEditMode ? 'Guardar cambios' : 'Crear recepción' }}
            </button>
          </div>
        </section>
      </form>
    </main>
  `,
  styles: [`
    .recepcion-form-shell { min-height: 100vh; background: #f4f7fb; padding: 2rem; color: #15304f; }
    .header { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; margin-bottom: 1.5rem; }
    .eyebrow { margin: 0 0 .35rem; text-transform: uppercase; letter-spacing: .12em; font-size: .78rem; color: #85711b; font-weight: 700; }
    h1, h2 { margin: 0; }
    .subtitle { margin: .5rem 0 0; color: #50667f; }
    .form-grid { display: grid; gap: 1rem; }
    .card { background: #fff; border-radius: 1.25rem; box-shadow: 0 18px 40px rgba(17, 48, 83, .08); padding: 1.25rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 1rem; }
    .field { display: flex; flex-direction: column; gap: .45rem; }
    .field span { font-weight: 600; color: #284c73; }
    .field input, .field select, .field textarea { border: 1px solid #c8d5e6; border-radius: .85rem; padding: .8rem .95rem; font: inherit; }
    .field-hint { margin: -.25rem 0 0; color: #5f7289; font-size: .88rem; }
    .field textarea { min-height: 110px; resize: vertical; }
    .field-wide { grid-column: 1 / -1; }
    .button { border: none; border-radius: .85rem; padding: .85rem 1.15rem; text-decoration: none; cursor: pointer; font-weight: 700; font: inherit; }
    .button.primary { background: #10386e; color: #fff; }
    .button.ghost { background: #edf3fa; color: #10386e; }
    .section-head, .header-actions, .submit-row { display: flex; justify-content: space-between; gap: .75rem; align-items: center; margin-bottom: 1rem; }
    .repeat-card { border: 1px solid #e1e9f3; border-radius: 1rem; padding: 1rem; margin-bottom: .9rem; }
    .inline-danger { border: none; background: transparent; color: #aa2c22; font-weight: 700; cursor: pointer; padding: 0; margin-top: .75rem; }
    .loading, .error { margin: 0; }
    .error { color: #b03b2d; }
    @media (max-width: 768px) {
      .recepcion-form-shell { padding: 1rem; }
      .header, .section-head, .submit-row { flex-direction: column; align-items: stretch; }
    }
  `],
})
export class RecepcionFormPageComponent implements OnInit {
  private readonly recepcionesService = inject(RecepcionesService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly session = getStoredSession();

  readonly fuelLevels: FuelLevel[] = ['vacio', '1/4', '1/2', '3/4', 'lleno'];
  readonly statusOptions: RecepcionStatus[] = [
    'registrada',
    'en_diagnostico',
    'en_trabajo',
    'finalizada',
    'entregada',
  ];
  readonly priorityOptions: ProblemaPriority[] = ['baja', 'media', 'alta'];

  isEditMode = false;
  recepcionId: number | null = null;
  isLoading = false;
  isLoadingMechanics = false;
  accessDenied = false;
  errorMessage = '';
  availableMechanics: RecepcionMechanicOption[] = [];

  form = {
    cliente: {
      full_name: '',
      identity_card: '',
      phone: '',
      email: '',
      address: '',
      mobile_client_id: null as number | null,
    },
    vehiculo: {
      plate: '',
      brand: '',
      model: '',
      year: new Date().getFullYear(),
      color: '',
      vin: '',
      engine_number: '',
    },
    ficha: {
      codigo_ficha: '',
      status: 'registrada' as RecepcionStatus,
      kilometraje: null as number | null,
      nivel_combustible: '' as FuelLevel | '',
      assigned_mecanico_id: null as number | null,
      observaciones_generales: '',
    },
  };
  accesorios: AccesorioForm[] = [{ name: '', quantity: 1, notes: '' }];
  problemas: ProblemaForm[] = [{ description: '', priority: '', reported_by: 'secretaria' }];

  get role(): AppRole | null {
    return this.session?.role ?? null;
  }

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    this.isEditMode = Boolean(idParam);
    this.recepcionId = idParam ? Number(idParam) : null;
    this.accessDenied = !this.hasPageAccess();

    if (this.accessDenied) {
      return;
    }

    this.loadAvailableMechanics();

    if (!this.isEditMode || !this.recepcionId) {
      return;
    }

    this.loadRecepcion();
  }

  addAccesorio(): void {
    this.accesorios.push({ name: '', quantity: 1, notes: '' });
  }

  removeAccesorio(index: number): void {
    this.accesorios.splice(index, 1);
    if (!this.accesorios.length) {
      this.addAccesorio();
    }
  }

  addProblema(): void {
    this.problemas.push({ description: '', priority: '', reported_by: 'secretaria' });
  }

  removeProblema(index: number): void {
    this.problemas.splice(index, 1);
    if (!this.problemas.length) {
      this.addProblema();
    }
  }

  submitForm(): void {
    if (this.accessDenied || this.isLoading) {
      return;
    }

    this.errorMessage = '';
    this.isLoading = true;
    const payload = this.buildPayload();

    if (this.isEditMode && this.recepcionId) {
      this.recepcionesService.actualizarRecepcion(this.recepcionId, payload).subscribe({
        next: async () => {
          this.isLoading = false;
          await this.router.navigate(['/recepciones', this.recepcionId]);
        },
        error: (error: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = this.resolveErrorMessage(error);
        },
      });
      return;
    }

    this.recepcionesService.crearRecepcion(payload).subscribe({
      next: async (response) => {
        this.isLoading = false;
        await this.router.navigate(['/recepciones', response.id]);
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = this.resolveErrorMessage(error);
      },
    });
  }

  private hasPageAccess(): boolean {
    if (this.isEditMode) {
      return this.role === 'admin' || this.role === 'secretaria';
    }

    return this.role === 'secretaria';
  }

  formatMechanicOption(mechanic: RecepcionMechanicOption): string {
    const phoneLabel = mechanic.phone?.trim() ? ` · ${mechanic.phone}` : '';
    return `${mechanic.full_name} · ${mechanic.email}${phoneLabel}`;
  }

  private loadAvailableMechanics(): void {
    this.isLoadingMechanics = true;
    this.recepcionesService.listarMecanicosAsignables().subscribe({
      next: (mechanics) => {
        this.availableMechanics = mechanics;
        this.isLoadingMechanics = false;
      },
      error: () => {
        this.availableMechanics = [];
        this.isLoadingMechanics = false;
      },
    });
  }

  private loadRecepcion(): void {
    if (!this.recepcionId) {
      return;
    }

    this.isLoading = true;
    this.recepcionesService.obtenerRecepcion(this.recepcionId).subscribe({
      next: (recepcion) => {
        this.form = {
          cliente: {
            full_name: recepcion.cliente.full_name,
            identity_card: recepcion.cliente.identity_card,
            phone: recepcion.cliente.phone,
            email: recepcion.cliente.email || '',
            address: recepcion.cliente.address || '',
            mobile_client_id: recepcion.cliente.mobile_client_id ?? null,
          },
          vehiculo: {
            plate: recepcion.vehiculo.plate,
            brand: recepcion.vehiculo.brand,
            model: recepcion.vehiculo.model,
            year: recepcion.vehiculo.year,
            color: recepcion.vehiculo.color,
            vin: recepcion.vehiculo.vin || '',
            engine_number: recepcion.vehiculo.engine_number || '',
          },
          ficha: {
            codigo_ficha: recepcion.ficha.codigo_ficha,
            status: recepcion.ficha.status,
            kilometraje: recepcion.ficha.kilometraje ?? null,
            nivel_combustible: recepcion.ficha.nivel_combustible || '',
            assigned_mecanico_id: recepcion.ficha.assigned_mecanico_id ?? null,
            observaciones_generales: recepcion.ficha.observaciones_generales || '',
          },
        };
        this.accesorios = recepcion.accesorios.length
          ? recepcion.accesorios.map((item) => ({
              name: item.name,
              quantity: item.quantity,
              notes: item.notes || '',
            }))
          : [{ name: '', quantity: 1, notes: '' }];
        this.problemas = recepcion.problemas.length
          ? recepcion.problemas.map((item) => ({
              description: item.description,
              priority: item.priority || '',
              reported_by: item.reported_by,
            }))
          : [{ description: '', priority: '', reported_by: 'secretaria' }];
        this.isLoading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = this.resolveErrorMessage(error);
      },
    });
  }

  private buildPayload(): RecepcionPayload {
    return {
      cliente: {
        full_name: this.form.cliente.full_name.trim(),
        identity_card: this.form.cliente.identity_card.trim(),
        phone: this.form.cliente.phone.trim(),
        email: this.form.cliente.email.trim() || null,
        address: this.form.cliente.address.trim() || null,
        mobile_client_id: this.form.cliente.mobile_client_id || null,
      },
      vehiculo: {
        plate: this.form.vehiculo.plate.trim(),
        brand: this.form.vehiculo.brand.trim(),
        model: this.form.vehiculo.model.trim(),
        year: Number(this.form.vehiculo.year),
        color: this.form.vehiculo.color.trim(),
        vin: this.form.vehiculo.vin.trim() || null,
        engine_number: this.form.vehiculo.engine_number.trim() || null,
      },
      ficha: {
        ...(this.isEditMode ? { codigo_ficha: this.form.ficha.codigo_ficha } : {}),
        ...(this.isEditMode ? { status: this.form.ficha.status } : {}),
        kilometraje: this.form.ficha.kilometraje,
        nivel_combustible: this.form.ficha.nivel_combustible || null,
        assigned_mecanico_id: this.form.ficha.assigned_mecanico_id || null,
        observaciones_generales: this.form.ficha.observaciones_generales.trim() || null,
      },
      accesorios: this.accesorios
        .filter((item) => item.name.trim())
        .map((item) => ({
          name: item.name.trim(),
          quantity: Number(item.quantity) || 1,
          notes: item.notes.trim() || null,
        })),
      problemas: this.problemas
        .filter((item) => item.description.trim())
        .map((item) => ({
          description: item.description.trim(),
          priority: item.priority || null,
          reported_by: item.reported_by,
        })),
    };
  }

  private resolveErrorMessage(error: HttpErrorResponse): string {
    const detail = error.error?.detail;

    if (error.status === 403) {
      return 'No tienes permisos para guardar esta recepción.';
    }

    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }

    if (error.status === 422 || error.status === 400) {
      return 'Revisa los campos obligatorios y vuelve a intentarlo.';
    }

    return this.isEditMode
      ? 'No se pudo actualizar la recepción.'
      : 'No se pudo crear la recepción.';
  }
}
