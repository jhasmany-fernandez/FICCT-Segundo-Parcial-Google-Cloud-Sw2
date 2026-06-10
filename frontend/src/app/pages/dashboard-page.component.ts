import { CommonModule, DatePipe } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, ElementRef, OnDestroy, ViewChild, inject } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { API_BASE_URL, BACKEND_BASE_URL } from '../api-base';
import { APP_SESSION_STORAGE_KEY, AppRole, AppSession, clearStoredSession, parseStoredSession } from '../session';
import { SucursalGraphqlService } from '../services/sucursal-graphql.service';

declare const L: any;

type DashboardSection =
  | 'dashboard'
  | 'workshops'
  | 'mecanicos'
  | 'secretarias'
  | 'clients'
  | 'maintenance'
  | 'emergencies'
  | 'reports'
  | 'audit';
type MecanicoStatus = 'disponible' | 'ocupado' | 'fuera_de_servicio';
type MecanicoFilter = 'activos' | 'todos' | 'historial';
type MaintenanceFilter = 'todas' | 'pendiente' | 'activo' | 'rechazado' | 'historial';
type SucursalEstado = 'ACTIVO' | 'INACTIVO';
type WorkshopApprovalStatus = SucursalEstado;
type ClientStatus = 'active' | 'suspended';
type AuditTone = 'info' | 'success' | 'warning' | 'danger';

const MECANICO_SPECIALTY_OPTIONS = [
  'Batería',
  'Neumático',
  'Combustible',
  'Motor',
  'Sistema eléctrico',
  'Accidente',
  'Cerrajería / llaves',
];

const WORKSHOP_ZONE_OPTIONS = [
  'zona norte',
  'zona sur',
  'zona este',
  'zona oeste',
  'zona centro',
];

const WORKSHOP_SPECIALTY_OPTIONS = [
  'Batería',
  'Neumático',
  'Combustible',
  'Motor',
  'Sistema eléctrico',
  'Accidente',
  'Cerrajería / llaves',
];

type DashboardStat = {
  label: string;
  value: string;
  detail: string;
  trend: string;
  tone: 'gold' | 'blue' | 'teal' | 'slate';
};

type DashboardItem = {
  title: string;
  subtitle: string;
  meta: string;
  priority: 'Alta' | 'Media' | 'Seguimiento';
};

type AuditItem = {
  title: string;
  detail: string;
  meta: string;
  createdAt: string;
  tone: AuditTone;
};

type MaintenanceRequest = {
  id: number;
  code: string;
  client: string;
  vehicle: string;
  location: string;
  priority: 'Alta' | 'Media' | 'Baja';
  status: 'pendiente' | 'activo' | 'rechazado';
  price: number | null;
  distance: string;
  detail: string;
  reportedAt: string;
  createdAt: string;
  latitude: number | null;
  longitude: number | null;
  nearestWorkshopId: number | null;
  nearestWorkshopName: string | null;
  problemType: string;
  standardizedProblemType: string | null;
  clientDescription: string | null;
  audioTranscript: string | null;
  photoUrls: string[];
  audioUrl: string | null;
  mapEmbedUrl: SafeResourceUrl | null;
  mapExternalUrl: string | null;
  assignmentId: number | null;
  assignmentStatus: string | null;
  assignedMecanicoId: number | null;
  assignedMecanicoName: string | null;
  assignedMecanicoPhone: string | null;
  assignedMecanicoSpecialty: string | null;
};

type EmergencyReport = {
  id: number;
  client_id: number | null;
  client_name: string | null;
  vehicle_name: string;
  vehicle_plate: string;
  problem_type: string;
  price: number | null;
  emergency_status: 'pendiente' | 'activo' | 'rechazado' | null;
  problem_type_standardized: string | null;
  description: string | null;
  audio_transcript: string | null;
  photo_paths?: string[] | string | null;
  photo_urls: string[] | string | null;
  audio_url: string | null;
  latitude: number | null;
  longitude: number | null;
  address: string | null;
  zone: string | null;
  nearest_workshop_id: number | null;
  nearest_workshop_name: string | null;
  nearest_workshop_specialty: string | null;
  nearest_workshop_zone: string | null;
  nearest_workshop_distance_meters: number | null;
  assignment_id: number | null;
  assignment_status: string | null;
  mecanico_id?: number | null;
  assigned_technician_id: number | null;
  assigned_technician_name: string | null;
  assigned_technician_phone: string | null;
  assigned_technician_email: string | null;
  assigned_technician_specialty: string | null;
  assigned_mecanico_id: number | null;
  assigned_mecanico_name: string | null;
  assigned_mecanico_phone: string | null;
  assigned_mecanico_email: string | null;
  assigned_mecanico_specialty: string | null;
  // Legacy API alias preserved for backward compatibility. Prefer assigned_mecanico_*.
  technician_id?: number | null;
  assigned_mechanic_id?: number | null;
  assigned_mechanic_name?: string | null;
  assigned_mechanic_phone?: string | null;
  assigned_mechanic_email?: string | null;
  assigned_mechanic_specialty?: string | null;
  mechanic_id?: number | null;
  created_at: string;
};

type Sucursal = {
  id: number;
  nombre: string;
  direccion: string;
  zona: string | null;
  telefono: string | null;
  email: string | null;
  latitud: number | null;
  longitud: number | null;
  horario_atencion: string | null;
  responsable: string | null;
  estado: SucursalEstado;
  fecha_registro: string;
  fecha_modificacion: string | null;
  mecanicos_activos_count?: number;
  secretarias_activas_count?: number;
  operativa?: boolean;
  motivo_no_operativa?: string;
};

type Secretaria = {
  id: number;
  cliente_id: number;
  sucursal_id: number;
  sucursal_nombre: string | null;
  sucursal_zona: string | null;
  sucursal_direccion: string | null;
  full_name: string;
  phone: string | null;
  email: string;
  status: string;
  created_at: string;
  updated_at: string;
};

type SecretariaFormModel = {
  full_name: string;
  phone: string;
  email: string;
  password: string;
  sucursal_id: number | null;
  status: string;
};

type Mecanico = {
  id: number;
  workshop_id: number | null;
  sucursal_id: number | null;
  sucursal_nombre: string | null;
  sucursal_zona: string | null;
  sucursal_direccion: string | null;
  full_name: string;
  phone: string;
  email: string;
  specialty: string;
  status: MecanicoStatus;
  created_at: string;
  updated_at: string;
};

type MecanicoFormModel = {
  full_name: string;
  phone: string;
  email: string;
  specialty: string;
  status: MecanicoStatus;
  sucursal_id: number | null;
};

type Client = {
  id: number;
  identity_card: string;
  full_name: string;
  email: string;
  phone: string;
  role: string;
  status: ClientStatus;
  accepted_terms: boolean;
  created_at: string;
  updated_at: string;
};

type ClientFormModel = {
  identity_card: string;
  full_name: string;
  email: string;
  phone: string;
  password: string;
  role: string;
  status: ClientStatus;
  accepted_terms: boolean;
};

type SucursalFormModel = {
  nombre: string;
  direccion: string;
  zona: string;
  telefono: string;
  email: string;
  latitud: number | null;
  longitud: number | null;
  horario_atencion: string;
  responsable: string;
  estado: SucursalEstado;
};

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [CommonModule, DatePipe, FormsModule, RouterLink, RouterLinkActive],
  template: `
    <main
      class="dashboard-page"
      [class.is-sidebar-collapsed]="isSidebarCollapsed"
      [class.is-exporting-report]="isExportingReport"
    >
      <aside class="dashboard-sidebar" [class.is-collapsed]="isSidebarCollapsed">
        <a class="dashboard-brand" routerLink="/">
          <span class="dashboard-brand-mark">
            <img src="/favicon.svg" alt="Logo ACB" />
          </span>
          <span>
            <strong>Emergencias Vehiculares</strong>
            <small>Centro de operaciones</small>
          </span>
        </a>

        <nav class="dashboard-menu">
          <div class="dashboard-menu-group">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'dashboard'"
              (click)="selectSection('dashboard')"
              *ngIf="canAccessSection('dashboard')"
            >
              <span class="dashboard-menu-icon">⌂</span>
              <span>Dashboard</span>
            </button>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessReceptionModule">
            <a
              class="dashboard-menu-link"
              routerLink="/fichas-recepcion"
              routerLinkActive="is-active"
            >
              <span class="dashboard-menu-icon">▤</span>
              <span>Fichas de Recepción</span>
            </a>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('workshops')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'workshops'"
              (click)="selectSection('workshops')"
            >
              <span class="dashboard-menu-icon">◫</span>
              <span>Sucursales</span>
              <span class="dashboard-menu-badge">Live</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'workshops'"
                (click)="selectSection('workshops')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Solicitudes</span>
                <strong>{{ sucursales.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('mecanicos')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'mecanicos'"
              (click)="selectSection('mecanicos')"
            >
              <span class="dashboard-menu-icon">◔</span>
              <span>Mecanicos</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'mecanicos'"
                (click)="selectSection('mecanicos')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Lista de Mecanicos</span>
                <strong>{{ mecanicos.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('secretarias')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'secretarias'"
              (click)="selectSection('secretarias')"
            >
              <span class="dashboard-menu-icon">◑</span>
              <span>Secretarias</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'secretarias'"
                (click)="selectSection('secretarias')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Lista de Secretarias</span>
                <strong>{{ secretarias.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('clients')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'clients'"
              (click)="selectSection('clients')"
            >
              <span class="dashboard-menu-icon">◉</span>
              <span>Clientes</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'clients'"
                (click)="selectSection('clients')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Lista de Clientes</span>
                <strong>{{ clients.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('emergencies')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'emergencies'"
              (click)="selectSection('emergencies')"
            >
              <span class="dashboard-menu-icon">⬒</span>
              <span>Emergencias</span>
              <span class="dashboard-menu-badge">24/7</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'emergencies'"
                (click)="selectSection('emergencies')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Solicitudes de emergencia</span>
                <strong>{{ maintenanceRequests.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('reports')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'reports'"
              (click)="selectSection('reports')"
            >
              <span class="dashboard-menu-icon">▥</span>
              <span>Reportes</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'reports'"
                (click)="selectSection('reports')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Trabajos realizados</span>
                <strong>{{ reportWorkRequests.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('audit')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'audit'"
              (click)="selectSection('audit')"
            >
              <span class="dashboard-menu-icon">▣</span>
              <span>Bitacora</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'audit'"
                (click)="selectSection('audit')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Actividad reciente</span>
                <strong>{{ auditItems.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>
        </nav>

        <section class="dashboard-sidebar-card">
          <span>Turno activo</span>
          <strong>{{ sidebarBranchTitle }}</strong>
          <p>{{ sidebarBranchDescription }}</p>
        </section>
      </aside>

      <section class="dashboard-content">
        <header class="dashboard-topbar">
          <div class="dashboard-topbar-copy">
            <button
              class="dashboard-sidebar-toggle"
              type="button"
              (click)="toggleSidebar()"
              [attr.aria-label]="isSidebarCollapsed ? 'Expandir menu lateral' : 'Contraer menu lateral'"
            >
              ☰
            </button>
            <span class="dashboard-topbar-kicker">Panel interno</span>
            <strong>{{ sectionTitle }}</strong>
            <small *ngIf="operationalBranchLabel">{{ operationalBranchLabel }}</small>
          </div>

          <div class="dashboard-topbar-actions">
            <div class="dashboard-user-pill">
              <span class="dashboard-user-avatar">{{ userInitials }}</span>
              <span class="dashboard-user-name">{{ userDisplayName }}</span>
            </div>

            <button
              class="dashboard-topbar-icon dashboard-notification-button"
              type="button"
              [class.has-alerts]="pendingEmergencyNotifications > 0"
              [attr.aria-label]="
                pendingEmergencyNotifications > 0
                  ? pendingEmergencyNotifications + ' emergencias pendientes'
                  : 'Notificaciones'
              "
              (click)="openEmergencyNotifications()"
            >
              🔔
              <span class="dashboard-notification-badge" *ngIf="pendingEmergencyNotifications > 0">
                {{ pendingEmergencyNotifications > 99 ? '99+' : pendingEmergencyNotifications }}
              </span>
            </button>

            <button
              class="dashboard-topbar-icon dashboard-topbar-logout"
              type="button"
              aria-label="Cerrar sesion"
              (click)="logout()"
            >
              ⎋
            </button>
          </div>
        </header>

        <section
          class="dashboard-stats"
          *ngIf="selectedSection === 'dashboard' || selectedSection === 'mecanicos' || selectedSection === 'clients'"
          [class.is-compact]="selectedSection === 'mecanicos' || selectedSection === 'clients'"
        >
          <article class="dashboard-stat-card" *ngFor="let stat of stats" [attr.data-tone]="stat.tone">
            <div class="dashboard-stat-top">
              <span>{{ stat.label }}</span>
              <small>{{ stat.trend }}</small>
            </div>
            <strong>{{ stat.value }}</strong>
            <p>{{ stat.detail }}</p>
          </article>
        </section>

        <section class="dashboard-grid">
          <article class="dashboard-panel dashboard-panel-accent" *ngIf="selectedSection === 'dashboard'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Actividad prioritaria</p>
                <h2>Solicitudes recientes</h2>
              </div>
              <a routerLink="/servicios">Ver servicios</a>
            </div>

            <div class="dashboard-list">
              <article class="dashboard-list-item" *ngFor="let item of requests">
                <div class="dashboard-list-copy">
                  <span class="dashboard-list-priority">{{ item.priority }}</span>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.subtitle }}</p>
                </div>
                <span class="dashboard-list-meta">{{ item.meta }}</span>
              </article>
            </div>
          </article>

          <article class="dashboard-panel" *ngIf="selectedSection === 'dashboard'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Resumen rápido</p>
                <h2>Radar de cobertura</h2>
              </div>
            </div>

            <div class="dashboard-coverage">
              <article class="dashboard-coverage-card">
                <span>Zonas activas</span>
                <strong>{{ uniqueZonesCount }}</strong>
                <p>Areas distintas con sucursales registradas desde el formulario.</p>
              </article>

              <article class="dashboard-coverage-card dashboard-coverage-card-highlight">
                <span>Último ingreso</span>
                <strong>{{ latestSucursalLabel }}</strong>
                <p>{{ latestSucursalDetail }}</p>
              </article>
            </div>

            <div class="dashboard-mini-list" *ngIf="recentSucursales.length">
              <article class="dashboard-mini-item" *ngFor="let sucursal of recentSucursales">
                <div>
                  <strong>{{ sucursal.nombre }}</strong>
                  <p>{{ sucursal.zona || 'Sin zona' }} · {{ sucursal.responsable || 'Sin responsable' }}</p>
                </div>
                <span>{{ sucursal.fecha_registro | date: 'shortTime' }}</span>
              </article>
            </div>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'emergencies'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Gestión de emergencias</p>
                <h2>Solicitudes de Emergencia</h2>
              </div>
              <div class="dashboard-toolbar">
                <button class="dashboard-refresh-button" type="button" (click)="loadEmergencies()">
                  Actualizar
                </button>
                <button class="dashboard-refresh-button" type="button" (click)="clearMaintenanceSearch()">
                  Limpiar filtros
                </button>
              </div>
            </div>

            <p class="dashboard-loading" *ngIf="isEmergenciesLoading">Cargando solicitudes de emergencia...</p>
            <p class="dashboard-empty" *ngIf="!isEmergenciesLoading && !maintenanceRequests.length">
              {{
                isWorkshopSession
                  ? 'No hay emergencias pendientes asignadas a esta sucursal.'
                  : isSecretariaSession
                    ? 'No hay emergencias asignadas a tu sucursal en este momento.'
                    : 'Aun no hay solicitudes de emergencia registradas.'
              }}
            </p>

            <section class="maintenance-topbar" *ngIf="!isEmergenciesLoading && maintenanceRequests.length">
              <article class="maintenance-summary-card maintenance-summary-card-compact">
                <div class="maintenance-summary-head">
                  <div>
                    <p class="dashboard-panel-kicker">Resumen de sucursal</p>
                    <h2>Panel rápido</h2>
                  </div>
                  <span class="maintenance-summary-total">{{ maintenanceRequestsFiltered.length }}</span>
                </div>
                <div class="maintenance-summary-list maintenance-summary-list-compact">
                  <div class="maintenance-summary-item" *ngFor="let item of maintenanceSummaryCounts">
                    <strong>{{ item.value }}</strong>
                    <span>{{ item.label }}</span>
                  </div>
                </div>
              </article>

              <div class="maintenance-toolbar maintenance-toolbar-compact">
                <div class="maintenance-toolbar-actions">
                  <button class="dashboard-refresh-button" type="button" (click)="loadEmergencies()">
                    Actualizar
                  </button>
                  <button class="dashboard-secondary-button" type="button" (click)="clearMaintenanceSearch()">
                    Limpiar
                  </button>
                </div>

                <label class="maintenance-search">
                  <span>Buscar por ID, cliente, vehículo o ubicación</span>
                  <input
                    type="search"
                    [(ngModel)]="maintenanceSearch"
                    placeholder="Buscar..."
                  />
                </label>

                <div class="maintenance-filter-buttons">
                  <button
                    type="button"
                    class="dashboard-secondary-button"
                    [class.is-active]="maintenanceFilter === 'todas'"
                    (click)="setMaintenanceFilter('todas')"
                  >
                    Todas
                  </button>
                  <button
                    type="button"
                    class="dashboard-secondary-button"
                    [class.is-active]="maintenanceFilter === 'pendiente'"
                    (click)="setMaintenanceFilter('pendiente')"
                  >
                    Pendiente
                  </button>
                  <button
                    type="button"
                    class="dashboard-secondary-button"
                    [class.is-active]="maintenanceFilter === 'activo'"
                    (click)="setMaintenanceFilter('activo')"
                  >
                    Activa
                  </button>
                  <button
                    type="button"
                    class="dashboard-secondary-button"
                    [class.is-active]="maintenanceFilter === 'rechazado'"
                    (click)="setMaintenanceFilter('rechazado')"
                  >
                    Rechazado
                  </button>
                  <button
                    type="button"
                    class="dashboard-secondary-button"
                    [class.is-active]="maintenanceFilter === 'historial'"
                    (click)="setMaintenanceFilter('historial')"
                  >
                    Historial
                  </button>
                </div>
              </div>
            </section>

            <div class="maintenance-layout" *ngIf="!isEmergenciesLoading && maintenanceRequests.length">
              <div class="maintenance-list-column">
                <div
                  class="maintenance-request-card"
                  *ngFor="let request of maintenanceRequestsFiltered"
                  [class.is-selected]="request.id === selectedMaintenanceRequestId"
                  (click)="selectMaintenanceRequest(request)"
                >
                  <div class="maintenance-request-header">
                    <strong>{{ request.code }}</strong>
                    <span class="maintenance-priority" [attr.data-priority]="request.priority">
                      {{ request.priority }}
                    </span>
                  </div>
                  <div class="maintenance-request-body">
                    <p class="maintenance-request-title">{{ request.client }}</p>
                    <p class="maintenance-request-subtitle">Vehículo: {{ request.vehicle }}</p>
                    <p class="maintenance-request-location">
                      {{ request.location }} · {{ request.distance }}
                    </p>
                    <p class="maintenance-request-detail">{{ request.detail }}</p>
                  </div>

                  <div class="maintenance-request-media" (click)="$event.stopPropagation()">
                    <div class="maintenance-request-map-preview" *ngIf="request.mapEmbedUrl; else requestNoMap">
                      <iframe
                        [src]="request.mapEmbedUrl"
                        loading="lazy"
                        referrerpolicy="no-referrer-when-downgrade"
                        title="Mapa de la emergencia"
                      ></iframe>
                      <a
                        *ngIf="request.mapExternalUrl"
                        [href]="request.mapExternalUrl"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Abrir mapa
                      </a>
                    </div>
                    <ng-template #requestNoMap>
                      <div class="maintenance-request-media-empty">
                        Mapa no disponible: esta solicitud no incluye coordenadas.
                      </div>
                    </ng-template>

                    <div class="maintenance-request-media-grid">
                      <div class="maintenance-request-audio-preview">
                        <strong>Audio</strong>
                        <audio
                          *ngIf="request.audioUrl; else requestNoAudio"
                          controls
                          [src]="request.audioUrl"
                        ></audio>
                        <ng-template #requestNoAudio>
                          <span>Sin audio enviado.</span>
                        </ng-template>
                      </div>

                      <div class="maintenance-request-photo-preview">
                        <strong>Imágenes enviadas por el cliente ({{ request.photoUrls.length }})</strong>
                        <div class="maintenance-request-photo-strip" *ngIf="request.photoUrls.length; else requestNoPhotos">
                          <a
                            *ngFor="let photoUrl of request.photoUrls"
                            [href]="photoUrl"
                            target="_blank"
                            rel="noreferrer"
                          >
                            <img [src]="photoUrl" alt="Foto de la emergencia" loading="lazy" />
                          </a>
                        </div>
                        <ng-template #requestNoPhotos>
                          <span>Sin fotos enviadas.</span>
                        </ng-template>
                      </div>
                    </div>
                  </div>

                  <div class="maintenance-request-footer">
                    <span class="maintenance-request-status" [attr.data-status]="request.status">
                      {{ request.status | titlecase }}
                    </span>
                    <span>{{ request.reportedAt }}</span>
                  </div>
                </div>
              </div>
            </div>
          </article>

          <article
            class="dashboard-panel dashboard-panel-wide reports-print-area"
            *ngIf="selectedSection === 'reports'"
          >
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Reportes</p>
                <h2>Trabajos realizados</h2>
              </div>
              <div class="dashboard-toolbar">
                <button class="dashboard-refresh-button" type="button" (click)="loadEmergencies()">
                  Actualizar
                </button>
                <button class="dashboard-refresh-button" type="button" (click)="exportReportsPdf()">
                  Exportar PDF
                </button>
              </div>
            </div>

            <section class="report-summary-grid">
              <article class="report-summary-item">
                <span>Sucursal / operador</span>
                <strong>{{ reportWorkshopName }}</strong>
              </article>
              <article class="report-summary-item">
                <span>Trabajos</span>
                <strong>{{ reportWorkRequests.length }}</strong>
              </article>
              <article class="report-summary-item">
                <span>Servicio</span>
                <strong>{{ formatReportPrice(reportTotalServiceAmount) }}</strong>
              </article>
              <article class="report-summary-item">
                <span>Monto</span>
                <strong>{{ formatReportPrice(reportTotalNetAmount) }}</strong>
              </article>
              <article class="report-summary-item">
                <span>Generado</span>
                <strong>{{ reportGeneratedAt | date: 'short' }}</strong>
              </article>
            </section>

            <p class="dashboard-loading" *ngIf="isEmergenciesLoading">Cargando trabajos realizados...</p>
            <p class="dashboard-empty" *ngIf="!isEmergenciesLoading && !reportWorkRequests.length">
              No hay trabajos realizados para esta sucursal.
            </p>

            <div class="dashboard-table-wrap report-table-wrap" *ngIf="!isEmergenciesLoading && reportWorkRequests.length">
              <table class="dashboard-table report-table">
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Fecha</th>
                    <th>Cliente</th>
                    <th>Vehículo</th>
                    <th>Problema</th>
                    <th>Mecánico</th>
                    <th>Estado</th>
                    <th>Servicio</th>
                    <th>Monto</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let request of reportWorkRequests">
                    <td data-label="Código">
                      <span class="dashboard-id-chip">{{ request.code }}</span>
                    </td>
                    <td data-label="Fecha">{{ request.createdAt | date: 'short' }}</td>
                    <td data-label="Cliente">{{ request.client }}</td>
                    <td data-label="Vehículo">{{ request.vehicle }}</td>
                    <td data-label="Problema">
                      {{ request.standardizedProblemType || request.problemType }}
                    </td>
                    <td data-label="Mecánico">
                      {{ request.assignedMecanicoName || 'Sin mecánico asignado' }}
                    </td>
                    <td data-label="Estado">
                      <span class="maintenance-request-status" [attr.data-status]="request.status">
                        {{ request.status | titlecase }}
                      </span>
                    </td>
                    <td data-label="Servicio">{{ formatReportPrice(calculateReportServiceAmount(request.price)) }}</td>
                    <td data-label="Monto">{{ formatReportPrice(calculateReportNetAmount(request.price)) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'audit'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Bitacora</p>
                <h2>Actividad reciente</h2>
              </div>
              <div class="dashboard-toolbar">
                <button class="dashboard-refresh-button" type="button" (click)="refreshAudit()">
                  Actualizar
                </button>
              </div>
            </div>

            <section class="audit-summary-grid">
              <article class="audit-summary-item">
                <span>Eventos</span>
                <strong>{{ auditItems.length }}</strong>
              </article>
              <article class="audit-summary-item">
                <span>Emergencias</span>
                <strong>{{ maintenanceRequests.length }}</strong>
              </article>
              <article class="audit-summary-item">
                <span>Mecánicos</span>
                <strong>{{ mecanicos.length }}</strong>
              </article>
              <article class="audit-summary-item">
                <span>Último evento</span>
                <strong>{{ auditLatestLabel }}</strong>
              </article>
            </section>

            <p class="dashboard-loading" *ngIf="isEmergenciesLoading || isMecanicosLoading || isLoading || isClientsLoading">
              Cargando actividad...
            </p>
            <p class="dashboard-empty" *ngIf="!isAuditLoading && !auditItems.length">
              Todavía no hay movimientos registrados para mostrar.
            </p>

            <div class="audit-timeline" *ngIf="!isAuditLoading && auditItems.length">
              <article class="audit-item" *ngFor="let item of auditItems" [attr.data-tone]="item.tone">
                <span class="audit-dot"></span>
                <div class="audit-card">
                  <div class="audit-card-head">
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.createdAt | date: 'short' }}</span>
                  </div>
                  <p>{{ item.detail }}</p>
                  <small>{{ item.meta }}</small>
                </div>
              </article>
            </div>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'workshops'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Administración operativa</p>
                <h2>Sucursales registradas</h2>
              </div>
              <div class="dashboard-toolbar">
                <span class="dashboard-toolbar-note">{{ sucursales.length }} registros cargados</span>
                <button
                  class="dashboard-secondary-button"
                  type="button"
                  *ngIf="canManageSucursales"
                  (click)="startSucursalCreate()"
                >
                  Registrar sucursal
                </button>
                <button class="dashboard-refresh-button" type="button" (click)="loadSucursales()">
                  Actualizar
                </button>
              </div>
            </div>

            <p class="dashboard-loading" *ngIf="isLoading">Cargando sucursales registradas...</p>
            <p class="dashboard-empty" *ngIf="!isLoading && !sucursales.length">
              Aun no hay sucursales registradas.
            </p>

            <div class="dashboard-table-wrap" *ngIf="!isLoading && sucursales.length">
              <table class="dashboard-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Sucursal</th>
                    <th>Dirección</th>
                    <th>Responsable</th>
                    <th>Contacto</th>
                    <th>Zona</th>
                    <th>Horario</th>
                    <th>Registro</th>
                    <th>Operativa</th>
                    <th>Estado</th>
                    <th>Opciones</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let sucursal of paginatedSucursales">
                    <td data-label="ID">
                      <span class="dashboard-id-chip">#{{ sucursal.id }}</span>
                    </td>
                    <td data-label="Sucursal">
                      <div class="dashboard-table-primary">
                        <strong>{{ sucursal.nombre }}</strong>
                        <span>{{ sucursal.estado }}</span>
                      </div>
                    </td>
                    <td data-label="Dirección">{{ sucursal.direccion }}</td>
                    <td data-label="Responsable">{{ sucursal.responsable || '-' }}</td>
                    <td data-label="Contacto">
                      <div class="dashboard-table-contact">
                        <strong>{{ sucursal.telefono || '-' }}</strong>
                        <span>{{ sucursal.email || '-' }}</span>
                      </div>
                    </td>
                    <td data-label="Zona">{{ sucursal.zona || '-' }}</td>
                    <td data-label="Horario">{{ sucursal.horario_atencion || '-' }}</td>
                    <td data-label="Registro">{{ sucursal.fecha_registro | date: 'short' }}</td>
                    <td data-label="Operativa">
                      <span class="dashboard-status-pill" [attr.data-status]="sucursal.operativa ? 'disponible' : 'rechazado'">
                        <span class="dashboard-status-dot"></span>
                        {{ sucursal.operativa ? 'Operativa' : 'No operativa' }}
                      </span>
                      <small *ngIf="!sucursal.operativa && sucursal.motivo_no_operativa" style="display:block;font-size:0.7rem;color:var(--text-muted,#888)">
                        {{ sucursal.motivo_no_operativa }}
                      </small>
                    </td>
                    <td data-label="Estado">
                      <button
                        class="dashboard-status-pill dashboard-status-button"
                        type="button"
                        [attr.data-status]="sucursal.estado === 'ACTIVO' ? 'activo' : 'rechazado'"
                        (click)="toggleSucursalStatus(sucursal)"
                        [attr.aria-label]="'Cambiar estado de ' + sucursal.nombre"
                        [disabled]="!canManageSucursales"
                      >
                        <span class="dashboard-status-dot"></span>
                        {{ sucursal.estado }}
                      </button>
                    </td>
                    <td data-label="Opciones">
                      <div class="sucursal-actions">
                        <button
                          class="mecanico-icon-button"
                          type="button"
                          (click)="editSucursal(sucursal)"
                          [attr.aria-label]="'Editar ' + sucursal.nombre"
                          title="Editar"
                          [disabled]="!canManageSucursales"
                        >
                          ✎
                        </button>
                        <button
                          class="mecanico-icon-button sucursal-delete-button"
                          type="button"
                          (click)="deleteSucursal(sucursal)"
                          [attr.aria-label]="'Inactivar ' + sucursal.nombre"
                          title="Inactivar"
                          [disabled]="!canManageSucursales"
                        >
                          🗑
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="dashboard-pagination" *ngIf="!isLoading && sucursales.length > sucursalesPageSize">
              <p class="dashboard-pagination-info">
                Mostrando {{ sucursalesRangeStart }}-{{ sucursalesRangeEnd }} de {{ sucursales.length }} registros
              </p>

              <div class="dashboard-pagination-actions">
                <button
                  class="dashboard-secondary-button"
                  type="button"
                  (click)="goToPreviousSucursalesPage()"
                  [disabled]="sucursalesPage === 1"
                >
                  Anterior
                </button>
                <span class="dashboard-pagination-page">Página {{ sucursalesPage }} / {{ sucursalesTotalPages }}</span>
                <button
                  class="dashboard-secondary-button"
                  type="button"
                  (click)="goToNextSucursalesPage()"
                  [disabled]="sucursalesPage === sucursalesTotalPages"
                >
                  Siguiente
                </button>
              </div>
            </div>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'mecanicos'">
            <div class="mecanico-crud">
              <div class="mecanico-crud-head">
                <div>
                  <p class="dashboard-panel-kicker">Gestion del equipo</p>
                  <h2>Gestionar Mecanicos</h2>
                </div>
                <button class="mecanico-create-button" type="button" (click)="startCreate()">
                  <span>+</span>
                  <span>{{ showMecanicoForm ? (editingMecanicoId ? 'Editar Mecanico' : 'Crear Mecanico') : 'Crear Mecanico' }}</span>
                </button>
              </div>

              <div class="mecanico-filter-tabs">
                <button
                  type="button"
                  class="mecanico-filter-tab"
                  [class.is-active]="mecanicoFilter === 'activos'"
                  (click)="mecanicoFilter = 'activos'"
                >
                  Activos
                </button>
                <button
                  type="button"
                  class="mecanico-filter-tab"
                  [class.is-active]="mecanicoFilter === 'todos'"
                  (click)="mecanicoFilter = 'todos'"
                >
                  Todos
                </button>
                <button
                  type="button"
                  class="mecanico-filter-tab"
                  [class.is-active]="mecanicoFilter === 'historial'"
                  (click)="mecanicoFilter = 'historial'"
                >
                  Historial
                </button>
              </div>

              <section class="mecanico-form-card" *ngIf="showMecanicoForm">
                <div class="mecanico-form-head">
                  <div>
                    <p class="dashboard-panel-kicker">Formulario</p>
                    <h3>{{ editingMecanicoId ? 'Editar mecanico' : 'Agregar mecanico' }}</h3>
                  </div>
                  <button class="dashboard-secondary-button" type="button" (click)="cancelMecanicoForm()">
                    Cerrar
                  </button>
                </div>

                <form class="mecanico-form mecanico-form-grid" (ngSubmit)="submitMecanico()">
                  <p
                    class="mecanico-form-feedback mecanico-field-wide"
                    *ngIf="!isActiveSucursalesLoading && !hasActiveSucursales"
                  >
                    Debe registrar al menos una sucursal activa antes de crear mecánicos.
                  </p>

                  <label class="mecanico-field">
                    <span>Nombre</span>
                    <input type="text" name="full_name" [(ngModel)]="mecanicoForm.full_name" required minlength="3" placeholder="Ej. Carlos Ramirez" />
                  </label>

                  <label class="mecanico-field">
                    <span>Telefono</span>
                    <input type="text" name="phone" [(ngModel)]="mecanicoForm.phone" required minlength="7" placeholder="Ej. 76324511" />
                  </label>

                  <label class="mecanico-field">
                    <span>Email</span>
                    <input type="email" name="email" [(ngModel)]="mecanicoForm.email" required placeholder="Ej. mecanico@correo.com" />
                  </label>

                  <label class="mecanico-field">
                    <span>Especialidad</span>
                    <select name="specialty" [(ngModel)]="mecanicoForm.specialty" required>
                      <option value="" disabled>Selecciona una especialidad</option>
                      <option *ngFor="let specialty of mecanicoSpecialtyOptions" [value]="specialty">
                        {{ specialty }}
                      </option>
                    </select>
                  </label>

                  <label class="mecanico-field mecanico-field-wide">
                    <span>Sucursal</span>
                    <select
                      name="sucursal_id"
                      [(ngModel)]="mecanicoForm.sucursal_id"
                      [disabled]="isActiveSucursalesLoading || !hasActiveSucursales || isSecretariaSession"
                      required
                    >
                      <option [ngValue]="null" disabled>
                        {{ isActiveSucursalesLoading ? 'Cargando sucursales activas...' : 'Selecciona una sucursal activa' }}
                      </option>
                      <option *ngFor="let sucursal of availableMecanicoSucursales" [ngValue]="sucursal.id">
                        {{ formatSucursalOptionLabel(sucursal) }}
                      </option>
                    </select>
                  </label>

                  <label class="mecanico-field mecanico-field-wide">
                    <span>Estado del mecanico</span>
                    <select name="status" [(ngModel)]="mecanicoForm.status" required>
                      <option value="disponible">Disponible</option>
                      <option value="ocupado">Ocupado</option>
                      <option value="fuera_de_servicio">Fuera de servicio</option>
                    </select>
                  </label>

                  <p class="mecanico-form-feedback mecanico-field-wide" *ngIf="mecanicoFeedback">
                    {{ mecanicoFeedback }}
                  </p>

                  <div class="mecanico-form-actions mecanico-field-wide">
                    <button
                      class="dashboard-refresh-button"
                      type="submit"
                      [disabled]="isSavingMecanico || isActiveSucursalesLoading || !hasActiveSucursales"
                    >
                      {{ isSavingMecanico ? 'Guardando...' : editingMecanicoId ? 'Guardar cambios' : 'Agregar Mecanico' }}
                    </button>
                    <button class="dashboard-secondary-button" type="button" (click)="resetMecanicoForm()">
                      Limpiar
                    </button>
                  </div>
                </form>
              </section>

              <section class="mecanico-table-card">
                <p class="dashboard-loading" *ngIf="isMecanicosLoading">Cargando mecanicos...</p>
                <p class="dashboard-empty" *ngIf="!isMecanicosLoading && !filteredMecanicos.length">
                  No hay mecanicos para el filtro seleccionado.
                </p>

                <div class="dashboard-table-wrap mecanico-table-wrap" *ngIf="!isMecanicosLoading && filteredMecanicos.length">
                  <table class="dashboard-table dashboard-table-mecanicos">
                    <thead>
                      <tr>
                        <th>Nombre</th>
                        <th>Telefono</th>
                        <th>Email</th>
                        <th>Especialidad</th>
                        <th>Sucursal</th>
                        <th>Estado</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let mecanico of filteredMecanicos">
                        <td data-label="Nombre">
                          <div class="dashboard-table-primary">
                            <strong>{{ mecanico.full_name }}</strong>
                            <span>Actualizado {{ mecanico.updated_at | date: 'shortDate' }}</span>
                          </div>
                        </td>
                        <td data-label="Telefono">{{ mecanico.phone }}</td>
                        <td data-label="Email">{{ mecanico.email }}</td>
                        <td data-label="Especialidad">{{ mecanico.specialty }}</td>
                        <td data-label="Sucursal">
                          <div class="dashboard-table-primary">
                            <strong>{{ mecanico.sucursal_nombre || 'Sin sucursal' }}</strong>
                            <span>{{ mecanico.sucursal_zona || mecanico.sucursal_direccion || 'Sin detalle' }}</span>
                          </div>
                        </td>
                        <td data-label="Estado">
                          <span class="dashboard-status-pill" [attr.data-status]="mecanico.status">
                            <span class="dashboard-status-dot"></span>
                            {{ statusLabel(mecanico.status) }}
                          </span>
                        </td>
                        <td data-label="Acciones">
                          <div class="mecanico-actions">
                            <button class="mecanico-inline-button" type="button" (click)="editMecanico(mecanico)">
                              Editar
                            </button>
                            <button class="mecanico-icon-button" type="button" (click)="deleteMecanico(mecanico)" aria-label="Eliminar mecanico">
                              🗑
                            </button>
                            <button class="mecanico-icon-button" type="button" (click)="toggleMecanicoStatus(mecanico)" aria-label="Cambiar estado">
                              ☰
                            </button>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'secretarias'">
            <div class="mecanico-crud">
              <div class="mecanico-crud-head">
                <div>
                  <p class="dashboard-panel-kicker">Gestion del equipo</p>
                  <h2>Gestionar Secretarias</h2>
                </div>
                <button
                  class="mecanico-create-button"
                  type="button"
                  (click)="startSecretariaCreate()"
                  *ngIf="isAdminSession"
                >
                  <span>+</span>
                  <span>{{ showSecretariaForm ? (editingSecretariaId ? 'Editar Secretaria' : 'Crear Secretaria') : 'Crear Secretaria' }}</span>
                </button>
              </div>

              <section class="mecanico-form-card" *ngIf="showSecretariaForm && isAdminSession">
                <div class="mecanico-form-head">
                  <div>
                    <p class="dashboard-panel-kicker">Formulario</p>
                    <h3>{{ editingSecretariaId ? 'Editar secretaria' : 'Agregar secretaria' }}</h3>
                  </div>
                  <button class="dashboard-secondary-button" type="button" (click)="cancelSecretariaForm()">
                    Cerrar
                  </button>
                </div>

                <form class="mecanico-form mecanico-form-grid" (ngSubmit)="submitSecretaria()">
                  <p
                    class="mecanico-form-feedback mecanico-field-wide"
                    *ngIf="!isActiveSucursalesLoading && !hasActiveSucursales"
                  >
                    Debe registrar al menos una sucursal activa antes de crear secretarias.
                  </p>

                  <label class="mecanico-field">
                    <span>Nombre completo</span>
                    <input type="text" name="sec_full_name" [(ngModel)]="secretariaForm.full_name" required minlength="3" placeholder="Ej. María Lopez" />
                  </label>

                  <label class="mecanico-field">
                    <span>Teléfono</span>
                    <input type="text" name="sec_phone" [(ngModel)]="secretariaForm.phone" placeholder="Ej. 76324511" />
                  </label>

                  <label class="mecanico-field">
                    <span>Email</span>
                    <input type="email" name="sec_email" [(ngModel)]="secretariaForm.email" required [attr.disabled]="editingSecretariaId ? true : null" placeholder="Ej. secretaria@correo.com" />
                  </label>

                  <label class="mecanico-field">
                    <span>{{ editingSecretariaId ? 'Contraseña (dejar vacío para no cambiar)' : 'Contraseña' }}</span>
                    <input
                      type="password"
                      name="sec_password"
                      [(ngModel)]="secretariaForm.password"
                      [required]="!editingSecretariaId"
                      minlength="6"
                      placeholder="{{ editingSecretariaId ? 'Nueva contraseña (opcional)' : 'Contraseña' }}"
                    />
                  </label>

                  <label class="mecanico-field mecanico-field-wide">
                    <span>Sucursal afiliada</span>
                    <select
                      name="sec_sucursal_id"
                      [(ngModel)]="secretariaForm.sucursal_id"
                      [disabled]="isActiveSucursalesLoading || !hasActiveSucursales"
                      required
                    >
                      <option [ngValue]="null" disabled>
                        {{ isActiveSucursalesLoading ? 'Cargando sucursales activas...' : 'Selecciona una sucursal activa' }}
                      </option>
                      <option *ngFor="let sucursal of activeSucursales" [ngValue]="sucursal.id">
                        {{ formatSucursalOptionLabel(sucursal) }}
                      </option>
                    </select>
                  </label>

                  <label class="mecanico-field mecanico-field-wide">
                    <span>Estado</span>
                    <select name="sec_status" [(ngModel)]="secretariaForm.status">
                      <option value="activo">Activo</option>
                      <option value="inactivo">Inactivo</option>
                    </select>
                  </label>

                  <p class="mecanico-form-feedback mecanico-field-wide" *ngIf="secretariaFeedback">
                    {{ secretariaFeedback }}
                  </p>

                  <div class="mecanico-form-actions mecanico-field-wide">
                    <button
                      class="dashboard-refresh-button"
                      type="submit"
                      [disabled]="isSavingSecretaria || isActiveSucursalesLoading || !hasActiveSucursales"
                    >
                      {{ isSavingSecretaria ? 'Guardando...' : editingSecretariaId ? 'Guardar cambios' : 'Agregar Secretaria' }}
                    </button>
                    <button class="dashboard-secondary-button" type="button" (click)="resetSecretariaForm()">
                      Limpiar
                    </button>
                  </div>
                </form>
              </section>

              <section class="mecanico-table-card">
                <p class="dashboard-loading" *ngIf="isSecretariasLoading">Cargando secretarias...</p>
                <p class="dashboard-empty" *ngIf="!isSecretariasLoading && !secretarias.length">
                  No hay secretarias registradas.
                </p>

                <div class="dashboard-table-wrap mecanico-table-wrap" *ngIf="!isSecretariasLoading && secretarias.length">
                  <table class="dashboard-table dashboard-table-mecanicos">
                    <thead>
                      <tr>
                        <th>Nombre</th>
                        <th>Teléfono</th>
                        <th>Email</th>
                        <th>Sucursal</th>
                        <th>Zona</th>
                        <th>Estado</th>
                        <th *ngIf="isAdminSession">Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let secretaria of secretarias">
                        <td data-label="Nombre">
                          <div class="dashboard-table-primary">
                            <strong>{{ secretaria.full_name }}</strong>
                          </div>
                        </td>
                        <td data-label="Teléfono">{{ secretaria.phone || '-' }}</td>
                        <td data-label="Email">{{ secretaria.email }}</td>
                        <td data-label="Sucursal">
                          <strong>{{ secretaria.sucursal_nombre || 'Sin sucursal' }}</strong>
                        </td>
                        <td data-label="Zona">{{ secretaria.sucursal_zona || '-' }}</td>
                        <td data-label="Estado">
                          <span class="dashboard-status-pill" [attr.data-status]="secretaria.status === 'activo' ? 'disponible' : 'fuera_de_servicio'">
                            <span class="dashboard-status-dot"></span>
                            {{ secretaria.status === 'activo' ? 'Activo' : 'Inactivo' }}
                          </span>
                        </td>
                        <td data-label="Acciones" *ngIf="isAdminSession">
                          <div class="sucursal-actions">
                            <button
                              class="mecanico-icon-button"
                              type="button"
                              title="Editar"
                              (click)="editSecretaria(secretaria)"
                            >✎</button>
                            <button
                              class="mecanico-icon-button sucursal-delete-button"
                              type="button"
                              title="Inactivar"
                              (click)="deleteSecretaria(secretaria)"
                            >✕</button>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'clients'">
            <div class="mecanico-crud">
              <div class="mecanico-crud-head">
                <div>
                  <p class="dashboard-panel-kicker">Usuarios registrados</p>
                  <h2>Lista de Clientes</h2>
                </div>
                <button class="dashboard-refresh-button" type="button" (click)="loadClients()">
                  Actualizar
                </button>
              </div>

              <section class="mecanico-table-card">
                <p class="dashboard-loading" *ngIf="isClientsLoading">Cargando clientes...</p>
                <p class="dashboard-empty" *ngIf="!isClientsLoading && !clients.length">
                  No hay clientes registrados.
                </p>

                <div class="dashboard-table-wrap mecanico-table-wrap" *ngIf="!isClientsLoading && clients.length">
                  <table class="dashboard-table dashboard-table-mecanicos">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Cliente</th>
                        <th>Carnet</th>
                        <th>Correo</th>
                        <th>Telefono</th>
                        <th>Rol</th>
                        <th>Estado</th>
                        <th>Registro</th>
                        <th>Opciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let client of clients">
                        <td data-label="ID">
                          <span class="dashboard-id-chip">#{{ client.id }}</span>
                        </td>
                        <td data-label="Cliente">
                          <div class="dashboard-table-primary">
                            <strong>{{ client.full_name }}</strong>
                            <span>{{ client.accepted_terms ? 'Terminos aceptados' : 'Pendiente de terminos' }}</span>
                          </div>
                        </td>
                        <td data-label="Carnet">{{ client.identity_card }}</td>
                        <td data-label="Correo">{{ client.email }}</td>
                        <td data-label="Telefono">{{ client.phone }}</td>
                        <td data-label="Rol">{{ client.role }}</td>
                        <td data-label="Estado">
                          <button
                            class="dashboard-status-pill dashboard-status-button"
                            type="button"
                            [attr.data-status]="client.status"
                            [attr.aria-label]="'Cambiar estado de ' + client.full_name"
                            (click)="toggleClientStatus(client)"
                          >
                            <span class="dashboard-status-dot"></span>
                            {{ clientStatusLabel(client.status) }}
                          </button>
                        </td>
                        <td data-label="Registro">{{ client.created_at | date: 'short' }}</td>
                        <td data-label="Opciones">
                          <div class="workshop-actions">
                            <button
                              class="mecanico-icon-button client-action-tooltip"
                              type="button"
                              (click)="editClient(client)"
                              [attr.aria-label]="'Editar ' + client.full_name"
                              data-tooltip="Editar"
                            >
                              ✎
                            </button>
                            <button
                              class="mecanico-icon-button workshop-delete-button client-action-tooltip"
                              type="button"
                              (click)="deleteClient(client)"
                              [attr.aria-label]="'Eliminar ' + client.full_name"
                              data-tooltip="Eliminar"
                            >
                              🗑
                            </button>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </article>
        </section>
      </section>

      <div class="dashboard-modal-backdrop" *ngIf="showSucursalEditModal" (click)="cancelSucursalEdit()">
        <section class="dashboard-modal-card" (click)="$event.stopPropagation()">
          <div class="dashboard-modal-head">
            <div>
              <p class="dashboard-panel-kicker">Gestión de sucursal</p>
              <h3>{{ editingSucursalId ? 'Actualizar sucursal' : 'Registrar sucursal' }}</h3>
            </div>
          </div>

          <form class="sucursal-edit-form" (ngSubmit)="submitSucursalEdit()">
            <label class="sucursal-edit-field">
              <span>Sucursal</span>
              <input
                type="text"
                name="nombre"
                [(ngModel)]="sucursalForm.nombre"
                required
                minlength="3"
              />
            </label>

            <label class="sucursal-edit-field">
              <span>Responsable</span>
              <input
                type="text"
                name="responsable"
                [(ngModel)]="sucursalForm.responsable"
                minlength="3"
              />
            </label>

            <label class="sucursal-edit-field">
              <span>Teléfono</span>
              <input
                type="text"
                name="telefono"
                [(ngModel)]="sucursalForm.telefono"
                minlength="7"
              />
            </label>

            <label class="sucursal-edit-field">
              <span>Correo Electrónico</span>
              <input
                type="email"
                name="email"
                [(ngModel)]="sucursalForm.email"
              />
            </label>

            <label class="sucursal-edit-field">
              <span>Dirección</span>
              <input
                type="text"
                name="direccion"
                [(ngModel)]="sucursalForm.direccion"
                required
                minlength="5"
              />
            </label>

            <label class="sucursal-edit-field">
              <span>Zona</span>
              <select name="zona" [(ngModel)]="sucursalForm.zona">
                <option value="">Selecciona una zona</option>
                <option *ngFor="let zone of sucursalZoneOptions" [value]="zone">{{ zone }}</option>
              </select>
            </label>

            <label class="sucursal-edit-field">
              <span>Horario de atención</span>
              <input
                type="text"
                name="horario_atencion"
                [(ngModel)]="sucursalForm.horario_atencion"
                placeholder="Lun-Vie 08:00-18:00"
              />
            </label>

            <label class="sucursal-edit-field">
              <span>Estado</span>
              <select name="estado" [(ngModel)]="sucursalForm.estado" required>
                <option value="ACTIVO">ACTIVO</option>
                <option value="INACTIVO">INACTIVO</option>
              </select>
            </label>

            <label class="sucursal-edit-field sucursal-edit-field-wide">
              <span>Ubicacion de la sucursal</span>
              <div class="sucursal-edit-map-field">
                <button
                  class="sucursal-edit-map-locate-button"
                  type="button"
                  (click)="locateSucursalEditCurrentPosition()"
                  [disabled]="isSucursalLocationLocating"
                  [attr.aria-label]="
                    isSucursalLocationLocating ? 'Obteniendo ubicación actual' : 'Usar ubicación actual'
                  "
                  [title]="
                    isSucursalLocationLocating
                      ? 'Ubicando...'
                      : isSecureContext
                        ? 'Usar ubicación actual'
                        : 'La ubicación automática requiere HTTPS o localhost'
                  "
                >
                  ⌖
                </button>
                <div
                  #sucursalEditMapCanvas
                  class="sucursal-edit-map-canvas"
                  aria-label="Mapa interactivo de ubicacion de la sucursal"
                ></div>
              </div>
              <div class="sucursal-edit-map-meta">
                <small>Haz clic en el mapa o arrastra el marcador para actualizar la ubicación.</small>
                <strong>
                  Lat: {{ formatCoordinate(sucursalForm.latitud) }} | Lng: {{ formatCoordinate(sucursalForm.longitud) }}
                </strong>
                <span class="sucursal-edit-map-status error" *ngIf="sucursalLocationMessage">
                  {{ sucursalLocationMessage }}
                </span>
              </div>
            </label>

            <p class="sucursal-edit-feedback" *ngIf="sucursalEditFeedback">
              {{ sucursalEditFeedback }}
            </p>

            <div class="sucursal-edit-actions">
              <button class="dashboard-refresh-button" type="submit" [disabled]="isSavingSucursal">
                {{ isSavingSucursal ? (editingSucursalId ? 'Actualizando...' : 'Registrando...') : (editingSucursalId ? 'Actualizar' : 'Registrar') }}
              </button>
              <button class="dashboard-secondary-button" type="button" (click)="cancelSucursalEdit()">
                Cancelar
              </button>
            </div>
          </form>
        </section>
      </div>

      <div class="dashboard-modal-backdrop" *ngIf="showClientEditModal" (click)="cancelClientEdit()">
        <section class="dashboard-modal-card" (click)="$event.stopPropagation()">
          <div class="dashboard-modal-head">
            <div>
              <p class="dashboard-panel-kicker">Edición de cliente</p>
              <h3>Actualizar cliente</h3>
            </div>
          </div>

          <form class="workshop-edit-form" (ngSubmit)="submitClientEdit()">
            <label class="workshop-edit-field">
              <span>Carnet</span>
              <input type="text" name="identity_card" [(ngModel)]="clientForm.identity_card" required minlength="5" />
            </label>

            <label class="workshop-edit-field">
              <span>Nombre completo</span>
              <input type="text" name="full_name" [(ngModel)]="clientForm.full_name" required minlength="3" />
            </label>

            <label class="workshop-edit-field">
              <span>Correo</span>
              <input type="email" name="email" [(ngModel)]="clientForm.email" required />
            </label>

            <label class="workshop-edit-field">
              <span>Telefono</span>
              <input type="text" name="phone" [(ngModel)]="clientForm.phone" required minlength="7" />
            </label>

            <label class="workshop-edit-field">
              <span>Nueva contraseña</span>
              <input
                type="password"
                name="password"
                [(ngModel)]="clientForm.password"
                minlength="6"
                placeholder="Dejar vacio para mantener la actual"
              />
            </label>

            <label class="workshop-edit-field">
              <span>Rol</span>
              <input type="text" name="role" [(ngModel)]="clientForm.role" required minlength="2" />
            </label>

            <label class="workshop-edit-field">
              <span>Estado</span>
              <select name="status" [(ngModel)]="clientForm.status" required>
                <option value="active">Activo</option>
                <option value="suspended">Desactivado</option>
              </select>
            </label>

            <label class="workshop-edit-field workshop-edit-field-wide">
              <span class="client-terms-row">
                <input type="checkbox" name="accepted_terms" [(ngModel)]="clientForm.accepted_terms" />
                <span>Terminos aceptados</span>
              </span>
            </label>

            <p class="workshop-edit-feedback" *ngIf="clientEditFeedback">
              {{ clientEditFeedback }}
            </p>

            <div class="workshop-edit-actions">
              <button class="dashboard-refresh-button" type="submit" [disabled]="isSavingClient">
                {{ isSavingClient ? 'Actualizando...' : 'Actualizar' }}
              </button>
              <button class="dashboard-secondary-button" type="button" (click)="cancelClientEdit()">
                Cancelar
              </button>
            </div>
          </form>
        </section>
      </div>

      <div class="dashboard-modal-backdrop" *ngIf="showClientDeleteModal" (click)="cancelClientDelete()">
        <section class="dashboard-modal-card" (click)="$event.stopPropagation()">
          <div class="dashboard-modal-head">
            <div>
              <p class="dashboard-panel-kicker">Edición de cliente</p>
              <h3>Eliminar cliente</h3>
            </div>
          </div>

          <div class="client-delete-modal-copy">
            <p>
              ¿Deseas eliminar a <strong>{{ clientPendingDelete?.full_name }}</strong>?
            </p>
            <p class="client-delete-modal-note">
              El registro se quitará de la lista de clientes, también se eliminarán sus vehículos registrados y esta acción no se podrá deshacer.
            </p>
          </div>

          <div class="workshop-edit-actions">
            <button class="client-delete-confirm-button" type="button" (click)="confirmClientDelete()">
              Eliminar cliente
            </button>
            <button class="dashboard-secondary-button" type="button" (click)="cancelClientDelete()">
              Cancelar
            </button>
          </div>
        </section>
      </div>

      <div class="dashboard-modal-backdrop" *ngIf="showEmergencyModal && selectedMaintenanceRequest" (click)="closeEmergencyModal()">
        <section class="dashboard-modal-card emergency-modal-card" (click)="$event.stopPropagation()">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-panel-kicker">Emergencia seleccionada</p>
              <h2>{{ selectedMaintenanceRequest.code }}</h2>
            </div>
            <button class="dashboard-secondary-button" type="button" (click)="closeEmergencyModal()">
              Cerrar
            </button>
          </div>

          <section class="maintenance-map-card">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Mapa</p>
                <h2>Ubicación</h2>
              </div>
            </div>
            <div class="maintenance-map-shell">
              <div #emergencyMapCanvas class="maintenance-map-canvas" aria-label="Mapa de la emergencia"></div>
              <div class="maintenance-map-overlay" *ngIf="!selectedEmergencyHasCoordinates">
                La emergencia seleccionada no tiene coordenadas disponibles.
              </div>
            </div>
            <p
              class="maintenance-map-legend"
              *ngIf="selectedMaintenanceRequest.nearestWorkshopName && selectedEmergencyHasCoordinates"
            >
              Ruta visual entre el cliente y la sucursal asignada:
              <strong>{{ selectedMaintenanceRequest.nearestWorkshopName }}</strong>
            </p>
          </section>

          <section class="maintenance-detail-card">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Detalle de emergencia</p>
                <h2>{{ selectedMaintenanceRequest.code }}</h2>
              </div>
            </div>
            <div class="emergency-detail-grid">
              <p><strong>Cliente:</strong> {{ selectedMaintenanceRequest.client }}</p>
              <p><strong>Vehículo:</strong> {{ selectedMaintenanceRequest.vehicle }}</p>
              <p><strong>Ubicación:</strong> {{ selectedMaintenanceRequest.location }}</p>
              <p *ngIf="selectedMaintenanceRequest.nearestWorkshopName">
                <strong>Sucursal asignada:</strong> {{ selectedMaintenanceRequest.nearestWorkshopName }}
              </p>
              <p><strong>Prioridad:</strong> {{ selectedMaintenanceRequest.priority }}</p>
              <p><strong>Estado:</strong> {{ selectedMaintenanceRequest.status | titlecase }}</p>
              <p><strong>Tipo reportado:</strong> {{ selectedMaintenanceRequest.problemType }}</p>
              <p *ngIf="selectedMaintenanceRequest.standardizedProblemType">
                <strong>Tipo estandarizado:</strong> {{ selectedMaintenanceRequest.standardizedProblemType }}
              </p>
              <p><strong>Servicio:</strong> {{ formatReportPrice(calculateReportServiceAmount(selectedMaintenanceRequest.price)) }}</p>
              <p><strong>Monto:</strong> {{ formatReportPrice(calculateReportNetAmount(selectedMaintenanceRequest.price)) }}</p>
            </div>

            <div class="emergency-detail-block">
              <strong>Resumen operativo</strong>
              <p>{{ selectedMaintenanceRequest.detail }}</p>
            </div>

            <div class="emergency-detail-block" *ngIf="selectedMaintenanceRequest.clientDescription">
              <strong>Descripción escrita por el cliente</strong>
              <p>{{ selectedMaintenanceRequest.clientDescription }}</p>
            </div>

            <div class="emergency-detail-block" *ngIf="selectedMaintenanceRequest.audioTranscript">
              <strong>Transcripción del audio</strong>
              <p>{{ selectedMaintenanceRequest.audioTranscript }}</p>
            </div>

            <div class="emergency-detail-block">
              <strong>Audio enviado</strong>
              <audio
                *ngIf="selectedMaintenanceRequest.audioUrl; else noEmergencyAudio"
                controls
                [src]="selectedMaintenanceRequest.audioUrl"
                class="emergency-audio-player"
              ></audio>
              <ng-template #noEmergencyAudio>
                <p class="emergency-empty-media">Esta emergencia no incluye audio.</p>
              </ng-template>
            </div>

            <div class="emergency-detail-block">
              <strong>Imágenes enviadas por el cliente</strong>
              <div class="emergency-photo-grid" *ngIf="selectedMaintenancePhotoUrls.length; else noEmergencyPhotos">
                <a
                  class="emergency-photo-item"
                  *ngFor="let photoUrl of selectedMaintenancePhotoUrls"
                  [href]="photoUrl"
                  target="_blank"
                  rel="noreferrer"
                >
                  <img [src]="photoUrl" alt="Imagen enviada por el cliente para la emergencia" />
                </a>
              </div>
              <ng-template #noEmergencyPhotos>
                <p class="emergency-empty-media">Esta emergencia no incluye imágenes.</p>
              </ng-template>
            </div>

            <div class="emergency-detail-block emergency-assignment-block" *ngIf="canManageEmergencies">
              <strong>Asignación de mecánico</strong>
              <div
                class="emergency-assigned-mecanico"
                *ngIf="selectedMaintenanceRequest.assignedMecanicoName; else noAssignedMecanico"
              >
                <p>
                  Mecánico asignado:
                  <strong>{{ selectedMaintenanceRequest.assignedMecanicoName }}</strong>
                  <span *ngIf="selectedMaintenanceRequest.assignedMecanicoPhone">
                    · {{ selectedMaintenanceRequest.assignedMecanicoPhone }}
                  </span>
                </p>
                <button
                  class="mecanico-inline-button"
                  type="button"
                  *ngIf="selectedMaintenanceRequest.status === 'activo' && !isEditingEmergencyAssignment"
                  (click)="startEmergencyAssignmentEdit()"
                >
                  Editar
                </button>
              </div>
              <ng-template #noAssignedMecanico>
                <p>
                  {{
                    selectedMaintenanceRequest.status === 'activo'
                      ? 'Selecciona un mecánico disponible para enviar asistencia.'
                      : 'Primero acepta la emergencia para habilitar la asignación.'
                  }}
                </p>
              </ng-template>

              <div
                class="emergency-assignment-controls"
                *ngIf="
                  selectedMaintenanceRequest.status === 'activo' &&
                  (!selectedMaintenanceRequest.assignedMecanicoId || isEditingEmergencyAssignment)
                "
              >
                <label class="mecanico-field">
                  <span>Mecánico disponible</span>
                  <select [(ngModel)]="selectedEmergencyMecanicoId" name="selectedEmergencyMecanicoId">
                    <option [ngValue]="null">Seleccionar mecánico</option>
                    <option *ngFor="let mecanico of assignableMecanicos" [ngValue]="mecanico.id">
                      {{ mecanico.full_name }} · {{ mecanico.specialty }} · {{ statusLabel(mecanico.status) }}
                    </option>
                  </select>
                </label>
                <button
                  class="dashboard-refresh-button"
                  type="button"
                  (click)="assignSelectedEmergencyMecanico()"
                  [disabled]="isAssigningEmergencyMecanico || !selectedEmergencyMecanicoId"
                >
                  {{ isAssigningEmergencyMecanico ? 'Asignando...' : 'Asignar mecánico' }}
                </button>
                <button
                  class="dashboard-secondary-button"
                  type="button"
                  *ngIf="selectedMaintenanceRequest.assignedMecanicoId"
                  (click)="cancelEmergencyAssignmentEdit()"
                  [disabled]="isAssigningEmergencyMecanico"
                >
                  Cancelar
                </button>
              </div>

              <p class="mecanico-form-feedback" *ngIf="emergencyAssignmentFeedback">
                {{ emergencyAssignmentFeedback }}
              </p>
            </div>
          </section>

          <div class="emergency-modal-actions">
            <ng-container *ngIf="canManageEmergencies">
              <button
                class="dashboard-refresh-button"
                type="button"
                *ngIf="selectedMaintenanceRequest.status === 'pendiente'"
                (click)="updateSelectedEmergencyStatus('activo')"
                [disabled]="isUpdatingEmergencyStatus"
              >
                {{ isUpdatingEmergencyStatus ? 'Actualizando...' : 'Aceptar' }}
              </button>
            </ng-container>
            <button
              class="client-delete-confirm-button"
              type="button"
              *ngIf="canRejectEmergencies"
              (click)="openEmergencyRejectModal(selectedMaintenanceRequest)"
              [disabled]="isUpdatingEmergencyStatus || rejectionSubmitting"
            >
              Rechazar
            </button>
            <ng-container *ngIf="isAdminSession">
              <button
                class="dashboard-danger-button"
                type="button"
                (click)="deleteSelectedEmergency()"
                [disabled]="isUpdatingEmergencyStatus"
              >
                Eliminar
              </button>
            </ng-container>
            <button
              class="dashboard-secondary-button"
              type="button"
              (click)="closeEmergencyModal()"
              [disabled]="isUpdatingEmergencyStatus || rejectionSubmitting"
            >
              Cancelar
            </button>
          </div>
        </section>
      </div>

      <div
        class="dashboard-modal-backdrop"
        *ngIf="showEmergencyModal && rejectingEmergency"
        (click)="closeEmergencyRejectModal()"
      >
        <section class="dashboard-modal-card reject-emergency-modal-card" (click)="$event.stopPropagation()">
          <div class="dashboard-modal-head">
            <div>
              <p class="dashboard-panel-kicker">Confirmación</p>
              <h3>Rechazar emergencia</h3>
            </div>
          </div>

          <div class="client-delete-modal-copy">
            <p>Escribe el motivo que recibirá el cliente.</p>
            <p class="client-delete-modal-note">
              Se notificará al cliente y la emergencia pasará a estado rechazado.
            </p>
          </div>

          <label class="reject-emergency-field">
            <span>Motivo del rechazo</span>
            <textarea
              name="rejectionReason"
              [(ngModel)]="rejectionReason"
              maxlength="500"
              rows="6"
              placeholder="Ej. No contamos con cobertura operativa inmediata para esta zona."
              [disabled]="rejectionSubmitting"
            ></textarea>
            <small class="reject-emergency-counter">{{ rejectionReason.length }}/500</small>
          </label>

          <p class="workshop-edit-feedback" *ngIf="rejectionError">
            {{ rejectionError }}
          </p>

          <div class="workshop-edit-actions">
            <button
              class="client-delete-confirm-button"
              type="button"
              (click)="submitEmergencyRejection()"
              [disabled]="rejectionSubmitting"
            >
              {{ rejectionSubmitting ? 'Confirmando...' : 'Confirmar rechazo' }}
            </button>
            <button
              class="dashboard-secondary-button"
              type="button"
              (click)="closeEmergencyRejectModal()"
              [disabled]="rejectionSubmitting"
            >
              Cancelar
            </button>
          </div>
        </section>
      </div>
    </main>
  `,
  styleUrl: './shared-pages.css',
})
export class DashboardPageComponent implements OnDestroy {
  readonly mecanicoSpecialtyOptions = MECANICO_SPECIALTY_OPTIONS;
  readonly sucursalZoneOptions = WORKSHOP_ZONE_OPTIONS;
  readonly isSecureContext = typeof window !== 'undefined' ? window.isSecureContext : false;
  private readonly http = inject(HttpClient);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly router = inject(Router);
  private readonly sucursalGql = inject(SucursalGraphqlService);
  private readonly mecanicosApiUrl = `${API_BASE_URL}/mecanicos`;
  private readonly sucursalesApiUrl = `${API_BASE_URL}/sucursales`;
  private readonly clientsApiUrl = `${API_BASE_URL}/clientes`;
  private readonly emergenciesApiUrl = `${API_BASE_URL}/emergencias`;
  private readonly backendBaseUrl = BACKEND_BASE_URL;
  private readonly appSessionStorageKey = APP_SESSION_STORAGE_KEY;
  private readonly emergencyRefreshMs = 15000;
  private readonly generalRefreshMs = 30000;
  private emergencyRefreshTimer: number | undefined;
  private generalRefreshTimer: number | undefined;
  private visibilityChangeHandler: (() => void) | undefined;

  readonly requests: DashboardItem[] = [
    {
      title: 'Cambio de bateria',
      subtitle: 'Cliente en Equipetrol, Santa Cruz',
      meta: 'Hace 8 min',
      priority: 'Alta',
    },
    {
      title: 'Remolque urbano',
      subtitle: 'Vehiculo detenido en Av. Banzer',
      meta: 'Hace 12 min',
      priority: 'Media',
    },
    {
      title: 'Falta de combustible',
      subtitle: 'Solicitud desde zona sur',
      meta: 'Hace 21 min',
      priority: 'Seguimiento',
    },
  ];

  maintenanceRequests: MaintenanceRequest[] = [];
  lastSeenPendingEmergencyId = 0;

  maintenanceSearch = '';
  maintenanceFilter: MaintenanceFilter = 'todas';
  selectedMaintenanceRequestId: number | null = null;
  selectedEmergencyMecanicoId: number | null = null;
  isEditingEmergencyAssignment = false;
  rejectingEmergency: MaintenanceRequest | null = null;
  rejectionReason = '';
  rejectionError = '';
  rejectionSubmitting = false;

  selectedSection: DashboardSection = 'dashboard';
  isSidebarCollapsed = false;
  isExportingReport = false;
  sucursales: Sucursal[] = [];
  activeSucursales: Sucursal[] = [];
  mecanicos: Mecanico[] = [];
  clients: Client[] = [];
  currentSecretaria: Secretaria | null = null;
  isLoading = true;
  isMecanicosLoading = true;
  isClientsLoading = true;
  isEmergenciesLoading = true;
  isActiveSucursalesLoading = true;
  isUpdatingEmergencyStatus = false;
  isAssigningEmergencyMecanico = false;
  isSavingMecanico = false;
  isSavingSucursal = false;
  isUpdatingSucursalStatus = false;
  isSavingClient = false;
  editingMecanicoId: number | null = null;
  editingSucursalId: number | null = null;
  editingClientId: number | null = null;
  secretarias: Secretaria[] = [];
  isSecretariasLoading = false;
  showSecretariaForm = false;
  editingSecretariaId: number | null = null;
  isSavingSecretaria = false;
  secretariaFeedback = '';
  secretariaForm: SecretariaFormModel = this.createEmptySecretariaForm();
  private readonly secretariasApiUrl = `${API_BASE_URL}/secretarias`;
  mecanicoFeedback = '';
  emergencyAssignmentFeedback = '';
  sucursalEditFeedback = '';
  clientEditFeedback = '';
  mecanicoFilter: MecanicoFilter = 'activos';
  showMecanicoForm = false;
  showSucursalEditModal = false;
  showClientEditModal = false;
  showClientDeleteModal = false;
  sucursalesPage = 1;
  readonly sucursalesPageSize = 15;
  private readonly adminSession: AppSession | null = this.readAdminSession();
  clientPendingDelete: Client | null = null;
  showEmergencyModal = false;
  private emergencyMap?: any;
  private emergencyMapMarkersLayer?: any;
  private emergencyMapResizeTimer?: number;
  private sucursalEditMap?: any;
  private sucursalEditMapMarker?: any;
  private sucursalEditMapResizeTimer?: number;
  private sucursalEditMapHost?: HTMLDivElement;
  isSucursalLocationLocating = false;
  sucursalLocationMessage = '';

  @ViewChild('emergencyMapCanvas')
  set emergencyMapCanvas(element: ElementRef<HTMLDivElement> | undefined) {
    if (!element || typeof window === 'undefined') {
      return;
    }

    window.setTimeout(() => {
      this.initializeEmergencyMap(element.nativeElement);
      this.renderSelectedEmergencyMap();
    });
  }

  @ViewChild('sucursalEditMapCanvas')
  set sucursalEditMapCanvas(element: ElementRef<HTMLDivElement> | undefined) {
    if (!element || typeof window === 'undefined' || !this.showSucursalEditModal) {
      return;
    }

    window.setTimeout(() => {
      this.initializeSucursalEditMap(element.nativeElement);
      this.renderSucursalEditMap();
    });
  }

  mecanicoForm: MecanicoFormModel = this.createEmptyMecanicoForm();
  sucursalForm: SucursalFormModel = this.createEmptySucursalForm();
  clientForm: ClientFormModel = this.createEmptyClientForm();

  stats: DashboardStat[] = [
    {
      label: 'Solicitudes hoy',
      value: '18',
      detail: 'Auxilios y consultas registradas durante la jornada.',
      trend: '+12%',
      tone: 'gold',
    },
    {
      label: 'Sucursales registradas',
      value: '0',
      detail: 'Registros creados desde el formulario publico.',
      trend: 'Actual',
      tone: 'blue',
    },
    {
      label: 'Mecanicos disponibles',
      value: '0',
      detail: 'Personal listo para atender solicitudes inmediatas.',
      trend: 'Equipo',
      tone: 'teal',
    },
    {
      label: 'Clientes activos',
      value: '0',
      detail: 'Usuarios listos para iniciar sesion desde la app movil.',
      trend: 'App',
      tone: 'blue',
    },
    {
      label: 'Cobertura',
      value: '0 zonas',
      detail: 'Ciudad, periferia y rutas con respuesta coordinada.',
      trend: 'Expandible',
      tone: 'slate',
    },
  ];

  constructor() {
    if (this.isWorkshopSession) {
      this.selectedSection = 'reports';
    }

    if (this.canRejectEmergencies) {
      this.maintenanceFilter = 'pendiente';
    }

    this.loadSucursales();
    this.loadActiveSucursales();
    this.loadMecanicos();
    this.loadClients();
    this.loadEmergencies();
    this.loadSecretarias();
    this.startEmergencyRefresh();
    this.startGeneralRefresh();
  }

  ngOnDestroy(): void {
    if (typeof window !== 'undefined' && this.emergencyRefreshTimer !== undefined) {
      window.clearInterval(this.emergencyRefreshTimer);
    }
    if (typeof window !== 'undefined' && this.generalRefreshTimer !== undefined) {
      window.clearInterval(this.generalRefreshTimer);
    }
    if (typeof document !== 'undefined' && this.visibilityChangeHandler) {
      document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
    }

    if (typeof window !== 'undefined' && this.emergencyMapResizeTimer !== undefined) {
      window.clearTimeout(this.emergencyMapResizeTimer);
    }

    if (typeof window !== 'undefined' && this.sucursalEditMapResizeTimer !== undefined) {
      window.clearTimeout(this.sucursalEditMapResizeTimer);
    }

    if (this.emergencyMap) {
      this.emergencyMap.remove();
      this.emergencyMap = undefined;
      this.emergencyMapMarkersLayer = undefined;
    }

    this.destroySucursalEditMap();
  }

  get sectionTitle(): string {
    if (this.selectedSection === 'mecanicos') {
      return 'Gestion de Mecanicos';
    }

    if (this.selectedSection === 'clients') {
      return 'Gestion de Clientes';
    }

    if (this.selectedSection === 'workshops') {
      return 'Gestion de Solicitudes';
    }

    if (this.selectedSection === 'maintenance') {
      return 'Mantenimiento';
    }

    if (this.selectedSection === 'emergencies') {
      return 'Solicitudes de emergencia';
    }

    if (this.selectedSection === 'reports') {
      return 'Reportes';
    }

    if (this.selectedSection === 'audit') {
      return 'Bitacora';
    }

    return 'Resumen general';
  }

  get userDisplayName(): string {
    return this.adminSession?.fullName?.trim() || 'Administrador';
  }

  get operationalBranchLabel(): string | null {
    if (!this.isSecretariaSession || !this.currentSecretaria?.sucursal_nombre) {
      return null;
    }

    return `Sucursal activa: ${this.currentSecretaria.sucursal_nombre}`;
  }

  get sidebarBranchTitle(): string {
    if (this.isSecretariaSession && this.currentSecretaria?.sucursal_nombre) {
      return this.currentSecretaria.sucursal_nombre;
    }

    return 'Administración general';
  }

  get sidebarBranchDescription(): string {
    if (this.isSecretariaSession && this.currentSecretaria?.sucursal_nombre) {
      const zoneOrAddress =
        this.currentSecretaria.sucursal_zona || this.currentSecretaria.sucursal_direccion || 'Sucursal afiliada';
      return `Operación enfocada en ${zoneOrAddress}. Solo verás emergencias y mecánicos afiliados a esta sucursal.`;
    }

    return 'Supervision de sucursales, coordinacion operativa y control del panel empresarial.';
  }

  get isAdminSession(): boolean {
    return this.adminSession?.role === 'admin';
  }

  get isWorkshopSession(): boolean {
    return this.adminSession?.role === 'workshop';
  }

  get isSecretariaSession(): boolean {
    return this.adminSession?.role === 'secretaria';
  }

  get isMecanicoSession(): boolean {
    return this.adminSession?.role === 'mecanico';
  }

  get canManageSucursales(): boolean {
    const role = this.adminSession?.role;
    return role === 'admin' || role === 'secretaria';
  }

  get canRejectEmergencies(): boolean {
    const role = this.adminSession?.role;
    return role === 'admin' || role === 'secretaria';
  }

  get canManageEmergencies(): boolean {
    return this.canRejectEmergencies;
  }

  get canAccessReceptionModule(): boolean {
    const role = this.adminSession?.role;
    return role === 'admin' || role === 'secretaria' || role === 'mecanico';
  }

  get currentWorkshopId(): number | null {
    return this.isWorkshopSession ? this.adminSession?.id ?? null : null;
  }

  get currentEmergencyScopeWorkshopId(): number | null {
    if (this.isWorkshopSession) {
      return this.currentWorkshopId;
    }

    if (this.isSecretariaSession) {
      return this.currentSecretaria?.sucursal_id ?? null;
    }

    return null;
  }

  get effectiveWorkshopIdForEmergency(): number | null {
    if (this.isSecretariaSession) {
      return this.selectedMaintenanceRequest?.nearestWorkshopId ?? this.currentEmergencyScopeWorkshopId;
    }
    if (this.isAdminSession) {
      return this.selectedMaintenanceRequest?.nearestWorkshopId ?? null;
    }
    return null;
  }

  canAccessSection(section: DashboardSection): boolean {
    const role = this.adminSession?.role as AppRole | undefined;

    if (role === 'admin') {
      return true;
    }

    if (role === 'workshop') {
      return section === 'mecanicos' || section === 'reports';
    }

    if (role === 'secretaria') {
      return (
        section === 'dashboard' ||
        section === 'mecanicos' ||
        section === 'clients' ||
        section === 'emergencies' ||
        section === 'reports'
      );
    }

    if (role === 'mecanico') {
      return section === 'dashboard';
    }

    return false;
  }

  get maintenanceRequestsFiltered(): MaintenanceRequest[] {
    return this.maintenanceRequests.filter((request) => {
      const matchesSearch = [request.code, request.client, request.vehicle, request.location, request.detail]
        .some((value) => value.toLowerCase().includes(this.maintenanceSearch.toLowerCase()));
      const matchesFilter =
        this.maintenanceFilter === 'todas' ||
        (this.maintenanceFilter === 'historial' && request.status !== 'pendiente') ||
        request.status === this.maintenanceFilter;
      return matchesSearch && matchesFilter;
    });
  }

  get selectedMaintenanceRequest(): MaintenanceRequest | null {
    return this.maintenanceRequests.find((request) => request.id === this.selectedMaintenanceRequestId) ?? null;
  }

  get assignableMecanicos(): Mecanico[] {
    const assignedMecanicoId = this.selectedMaintenanceRequest?.assignedMecanicoId ?? null;
    const emergencySucursalId = this.selectedMaintenanceRequest?.nearestWorkshopId ?? null;

    return this.mecanicos.filter((mecanico) => {
      const inSucursal = emergencySucursalId === null || mecanico.sucursal_id === emergencySucursalId;
      return inSucursal && (mecanico.status === 'disponible' || mecanico.id === assignedMecanicoId);
    });
  }

  get maintenanceSummaryCounts(): { label: string; value: number }[] {
    return [
      { label: 'Urgentes', value: this.maintenanceRequests.filter((request) => request.priority === 'Alta').length },
      { label: 'Pendientes', value: this.maintenanceRequests.filter((request) => request.status === 'pendiente').length },
      { label: 'Activas', value: this.maintenanceRequests.filter((request) => request.status === 'activo').length },
    ];
  }

  get pendingEmergencyNotifications(): number {
    return this.maintenanceRequests.filter(
      (request) => request.status === 'pendiente' && request.id > this.lastSeenPendingEmergencyId,
    ).length;
  }

  get reportWorkRequests(): MaintenanceRequest[] {
    return this.maintenanceRequests.filter((request) => request.status === 'activo');
  }

  get reportTotalServiceAmount(): number {
    return this.reportWorkRequests.reduce(
      (total, request) => total + (this.calculateReportServiceAmount(request.price) ?? 0),
      0,
    );
  }

  get reportTotalNetAmount(): number {
    return this.reportWorkRequests.reduce(
      (total, request) => total + (this.calculateReportNetAmount(request.price) ?? 0),
      0,
    );
  }

  get reportWorkshopName(): string {
    return this.isWorkshopSession ? this.userDisplayName : 'Todas las sucursales';
  }

  get reportGeneratedAt(): Date {
    return new Date();
  }

  get isAuditLoading(): boolean {
    return this.isEmergenciesLoading || this.isMecanicosLoading || (!this.isWorkshopSession && (this.isLoading || this.isClientsLoading));
  }

  get auditItems(): AuditItem[] {
    const items: AuditItem[] = [];

    for (const request of this.maintenanceRequests) {
      items.push({
        title: `${request.code} registrada`,
        detail: `${request.client} solicito atencion para ${request.vehicle}.`,
        meta: `${request.problemType} · ${request.location}`,
        createdAt: request.createdAt,
        tone: request.status === 'rechazado' ? 'danger' : request.status === 'activo' ? 'success' : 'warning',
      });

      if (request.status === 'activo') {
        items.push({
          title: `${request.code} aceptada`,
          detail: `${request.nearestWorkshopName || this.reportWorkshopName} acepto la emergencia.`,
          meta: request.assignedMecanicoName
            ? `Mecanico asignado: ${request.assignedMecanicoName}`
            : 'Pendiente de asignacion mecanica',
          createdAt: request.createdAt,
          tone: 'success',
        });
      }

      if (request.status === 'rechazado') {
        items.push({
          title: `${request.code} rechazada`,
          detail: `${request.nearestWorkshopName || this.reportWorkshopName} rechazo la solicitud.`,
          meta: request.problemType,
          createdAt: request.createdAt,
          tone: 'danger',
        });
      }
    }

    for (const mecanico of this.mecanicos) {
      items.push({
        title: `Mecanico ${this.statusLabel(mecanico.status).toLowerCase()}`,
        detail: mecanico.full_name,
        meta: `${mecanico.specialty} · ${mecanico.phone}`,
        createdAt: mecanico.updated_at || mecanico.created_at,
        tone: mecanico.status === 'disponible' ? 'success' : mecanico.status === 'ocupado' ? 'warning' : 'info',
      });
    }

    if (!this.isWorkshopSession) {
      for (const sucursal of this.sucursales) {
        items.push({
          title: `Sucursal ${this.sucursalStatusLabel(sucursal.estado).toLowerCase()}`,
          detail: sucursal.nombre,
          meta: `${sucursal.zona || 'Sin zona'} · ${sucursal.responsable || 'Sin responsable'}`,
          createdAt: sucursal.fecha_registro,
          tone: sucursal.estado === 'ACTIVO' ? 'success' : 'warning',
        });
      }

      for (const client of this.clients) {
        items.push({
          title: `Cliente ${this.clientStatusLabel(client.status).toLowerCase()}`,
          detail: client.full_name,
          meta: `${client.email} · ${client.phone}`,
          createdAt: client.updated_at || client.created_at,
          tone: client.status === 'active' ? 'success' : 'warning',
        });
      }
    }

    return items
      .filter((item) => !Number.isNaN(new Date(item.createdAt).getTime()))
      .sort((first, second) => new Date(second.createdAt).getTime() - new Date(first.createdAt).getTime())
      .slice(0, 80);
  }

  get auditLatestLabel(): string {
    const latest = this.auditItems[0];

    if (!latest) {
      return 'Sin eventos';
    }

    return this.relativeTimeLabel(latest.createdAt);
  }

  selectMaintenanceRequest(request: MaintenanceRequest): void {
    this.selectedMaintenanceRequestId = request.id;
    this.selectedEmergencyMecanicoId = request.assignedMecanicoId;
    this.isEditingEmergencyAssignment = false;
    this.emergencyAssignmentFeedback = '';
    this.showEmergencyModal = true;
    this.renderSelectedEmergencyMap();
  }

  setMaintenanceFilter(filter: MaintenanceFilter): void {
    this.maintenanceFilter = filter;
  }

  clearMaintenanceSearch(): void {
    this.maintenanceSearch = '';
    this.maintenanceFilter = this.isWorkshopSession ? 'pendiente' : 'todas';
  }

  exportReportsPdf(): void {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return;
    }

    const previousTitle = document.title;
    this.isExportingReport = true;
    document.title = `Reporte trabajos realizados - ${this.reportWorkshopName}`;

    window.setTimeout(() => {
      window.print();
      document.title = previousTitle;
      this.isExportingReport = false;
    });
  }

  refreshAudit(): void {
    this.loadEmergencies();
    this.loadMecanicos();

    if (!this.isWorkshopSession) {
      this.loadSucursales();
      this.loadClients();
    }
  }

  closeEmergencyModal(): void {
    this.showEmergencyModal = false;
    this.selectedEmergencyMecanicoId = null;
    this.isEditingEmergencyAssignment = false;
    this.emergencyAssignmentFeedback = '';
    this.closeEmergencyRejectModal();
  }

  openEmergencyRejectModal(report: MaintenanceRequest): void {
    if (!this.canRejectEmergencies || this.rejectionSubmitting) {
      return;
    }

    this.rejectingEmergency = report;
    this.rejectionReason = '';
    this.rejectionError = '';
  }

  closeEmergencyRejectModal(): void {
    if (this.rejectionSubmitting) {
      return;
    }

    this.rejectingEmergency = null;
    this.rejectionReason = '';
    this.rejectionError = '';
  }

  submitEmergencyRejection(): void {
    const selected = this.rejectingEmergency;
    const motivo = this.rejectionReason.trim();

    if (!selected || this.rejectionSubmitting) {
      return;
    }

    if (!motivo) {
      this.rejectionError = 'Debes escribir un motivo de rechazo.';
      return;
    }

    if (motivo.length < 5) {
      this.rejectionError = 'El motivo debe tener al menos 5 caracteres.';
      return;
    }

    if (motivo.length > 500) {
      this.rejectionError = 'El motivo no puede superar los 500 caracteres.';
      return;
    }

    this.rejectionSubmitting = true;
    this.rejectionError = '';

    this.http
      .post<EmergencyReport>(`${this.emergenciesApiUrl}/${selected.id}/rechazar`, { motivo })
      .subscribe({
        next: () => {
          this.rejectionSubmitting = false;
          this.closeEmergencyRejectModal();
          this.closeEmergencyModal();
          this.loadEmergencies();
          window.alert('Emergencia rechazada y cliente notificado.');
        },
        error: (error) => {
          this.rejectionSubmitting = false;
          this.rejectionError = this.extractHttpErrorMessage(
            error,
            'No se pudo rechazar la emergencia. Intenta nuevamente.',
          );
        },
      });
  }

  startEmergencyAssignmentEdit(): void {
    this.selectedEmergencyMecanicoId = this.selectedMaintenanceRequest?.assignedMecanicoId ?? null;
    this.isEditingEmergencyAssignment = true;
    this.emergencyAssignmentFeedback = '';
  }

  cancelEmergencyAssignmentEdit(): void {
    this.selectedEmergencyMecanicoId = this.selectedMaintenanceRequest?.assignedMecanicoId ?? null;
    this.isEditingEmergencyAssignment = false;
    this.emergencyAssignmentFeedback = '';
  }

  updateSelectedEmergencyStatus(nextStatus: 'activo'): void {
    const selected = this.selectedMaintenanceRequest;

    if (!selected || this.isUpdatingEmergencyStatus) {
      return;
    }

    this.isUpdatingEmergencyStatus = true;

    this.http
      .put<EmergencyReport>(
        `${this.emergenciesApiUrl}/${selected.id}/status`,
        { emergency_status: nextStatus },
        {
          params: this.effectiveWorkshopIdForEmergency ? { workshop_id: this.effectiveWorkshopIdForEmergency } : {},
        },
      )
      .subscribe({
        next: (updatedReport) => {
          const updatedRequest = this.mapEmergencyReportToRequest(updatedReport);
          this.maintenanceRequests = this.maintenanceRequests.map((request) =>
            request.id === updatedRequest.id ? updatedRequest : request,
          );
          this.selectedMaintenanceRequestId = updatedRequest.id;
          this.selectedEmergencyMecanicoId = updatedRequest.assignedMecanicoId;
          this.isUpdatingEmergencyStatus = false;
          this.emergencyAssignmentFeedback = 'Emergencia aceptada. Selecciona un mecánico de la sucursal para enviar asistencia.';

          if (nextStatus === 'activo') {
            this.maintenanceFilter = 'activo';
          }
        },
        error: (error) => {
          this.isUpdatingEmergencyStatus = false;
          window.alert(this.extractHttpErrorMessage(error, 'No se pudo actualizar el estado de la emergencia.'));
        },
      });
  }

  assignSelectedEmergencyMecanico(): void {
    const selected = this.selectedMaintenanceRequest;
    const workshopId = this.effectiveWorkshopIdForEmergency;

    if (
      !selected ||
      !workshopId ||
      !this.selectedEmergencyMecanicoId ||
      this.isAssigningEmergencyMecanico
    ) {
      return;
    }

    if (selected.status !== 'activo') {
      this.emergencyAssignmentFeedback = 'Primero acepta la emergencia para asignar un mecanico.';
      return;
    }

    this.isAssigningEmergencyMecanico = true;
    this.emergencyAssignmentFeedback = '';

    this.http
      .put<EmergencyReport>(
        `${this.emergenciesApiUrl}/${selected.id}/mechanic-assignment`,
        { mecanico_id: this.selectedEmergencyMecanicoId },
        { params: { workshop_id: workshopId } },
      )
      .subscribe({
        next: (updatedReport) => {
          const updatedRequest = this.mapEmergencyReportToRequest(updatedReport);
          this.maintenanceRequests = this.maintenanceRequests.map((request) =>
            request.id === updatedRequest.id ? updatedRequest : request,
          );
          this.selectedMaintenanceRequestId = updatedRequest.id;
          this.selectedEmergencyMecanicoId = updatedRequest.assignedMecanicoId;
          this.isEditingEmergencyAssignment = false;
          this.isAssigningEmergencyMecanico = false;
          this.closeEmergencyModal();
          this.loadEmergencies();
          this.loadMecanicos();
        },
        error: () => {
          this.isAssigningEmergencyMecanico = false;
          this.emergencyAssignmentFeedback = 'No se pudo asignar el mecanico seleccionado.';
        },
      });
  }

  deleteSelectedEmergency(): void {
    const selected = this.selectedMaintenanceRequest;

    if (!selected || this.isUpdatingEmergencyStatus) {
      return;
    }

    const confirmed = window.confirm(`¿Deseas eliminar la solicitud ${selected.code}?`);

    if (!confirmed) {
      return;
    }

    this.isUpdatingEmergencyStatus = true;

    this.http
      .delete(`${this.emergenciesApiUrl}/${selected.id}`, {
        params: this.currentEmergencyScopeWorkshopId ? { workshop_id: this.currentEmergencyScopeWorkshopId } : {},
      })
      .subscribe({
        next: () => {
          this.isUpdatingEmergencyStatus = false;
          this.closeEmergencyModal();
          this.loadEmergencies();
        },
        error: () => {
          this.isUpdatingEmergencyStatus = false;
          window.alert('No se pudo eliminar la emergencia.');
        },
      });
  }

  loadEmergencies(silent = false): void {
    if (!silent) {
      this.isEmergenciesLoading = true;
    }

    const params: Record<string, string> = {};

    // Para secretaria dejamos que el backend aplique su propio alcance por sucursal
    // y evitemos un doble filtrado que puede ocultar emergencias válidas.
    if (this.isWorkshopSession && this.currentEmergencyScopeWorkshopId) {
      params['nearest_workshop_id'] = String(this.currentEmergencyScopeWorkshopId);
    }

    this.http.get<EmergencyReport[]>(this.emergenciesApiUrl, { params }).subscribe({
      next: (reports) => {
        const previousSelectedId = this.selectedMaintenanceRequestId;
        this.maintenanceRequests = reports.map((report) => this.mapEmergencyReportToRequest(report));
        const previousSelectionStillExists = this.maintenanceRequests.some((request) => request.id === previousSelectedId);
        this.selectedMaintenanceRequestId = previousSelectionStillExists
          ? previousSelectedId
          : this.maintenanceRequests[0]?.id ?? null;
        if (!silent) {
          this.isEmergenciesLoading = false;
        }
        if (!silent || this.selectedMaintenanceRequestId !== previousSelectedId) {
          this.renderSelectedEmergencyMap();
        }
      },
      error: () => {
        if (!silent) {
          this.maintenanceRequests = [];
          this.selectedMaintenanceRequestId = null;
          this.isEmergenciesLoading = false;
          this.renderSelectedEmergencyMap();
        }
      },
    });
  }

  openEmergencyNotifications(): void {
    this.markPendingEmergenciesAsSeen();
    this.maintenanceFilter = 'pendiente';
    this.maintenanceSearch = '';
    this.selectSection('emergencies');
    this.loadEmergencies();
  }

  private markPendingEmergenciesAsSeen(): void {
    const latestPendingEmergencyId = this.maintenanceRequests
      .filter((request) => request.status === 'pendiente')
      .reduce((latestId, request) => Math.max(latestId, request.id), this.lastSeenPendingEmergencyId);

    this.lastSeenPendingEmergencyId = latestPendingEmergencyId;
  }

  private startEmergencyRefresh(): void {
    if (typeof window === 'undefined') {
      return;
    }

    this.emergencyRefreshTimer = window.setInterval(() => {
      this.loadEmergencies(true);
    }, this.emergencyRefreshMs);
  }

  private startGeneralRefresh(): void {
    if (typeof window === 'undefined') {
      return;
    }

    const refreshAll = () => {
      this.loadMecanicos();
      if (!this.isWorkshopSession) {
        this.loadSucursales();
        this.loadActiveSucursales();
        this.loadClients();
        this.loadSecretarias();
      }
    };

    this.generalRefreshTimer = window.setInterval(refreshAll, this.generalRefreshMs);

    this.visibilityChangeHandler = () => {
      if (document.visibilityState === 'visible') {
        this.loadEmergencies(true);
        refreshAll();
      }
    };
    document.addEventListener('visibilitychange', this.visibilityChangeHandler);
  }

  private getEmergencyAssignedMecanicoId(report: EmergencyReport): number | null {
    // Legacy API alias preserved for backward compatibility. Prefer assigned_mecanico_*.
    return (
      report.assigned_mecanico_id ??
      report.mecanico_id ??
      report.assigned_mechanic_id ??
      report.mechanic_id ??
      report.assigned_technician_id ??
      report.technician_id ??
      null
    );
  }

  private getEmergencyAssignedMecanicoName(report: EmergencyReport): string | null {
    // Legacy API alias preserved for backward compatibility. Prefer assigned_mecanico_*.
    return (
      report.assigned_mecanico_name ??
      report.assigned_mechanic_name ??
      report.assigned_technician_name ??
      null
    );
  }

  private getEmergencyAssignedMecanicoPhone(report: EmergencyReport): string | null {
    // Legacy API alias preserved for backward compatibility. Prefer assigned_mecanico_*.
    return (
      report.assigned_mecanico_phone ??
      report.assigned_mechanic_phone ??
      report.assigned_technician_phone ??
      null
    );
  }

  private getEmergencyAssignedMecanicoSpecialty(report: EmergencyReport): string | null {
    // Legacy API alias preserved for backward compatibility. Prefer assigned_mecanico_*.
    return (
      report.assigned_mecanico_specialty ??
      report.assigned_mechanic_specialty ??
      report.assigned_technician_specialty ??
      null
    );
  }

  private normalizeEmergencyReport(report: EmergencyReport): EmergencyReport {
    return {
      ...report,
      assigned_mecanico_id: this.getEmergencyAssignedMecanicoId(report),
      assigned_mecanico_name: this.getEmergencyAssignedMecanicoName(report),
      assigned_mecanico_phone: this.getEmergencyAssignedMecanicoPhone(report),
      assigned_mecanico_specialty: this.getEmergencyAssignedMecanicoSpecialty(report),
    };
  }

  private extractHttpErrorMessage(error: unknown, fallback: string): string {
    if (error instanceof HttpErrorResponse) {
      const detail = error.error?.detail;

      if (typeof detail === 'string' && detail.trim()) {
        return detail.trim();
      }

      if (Array.isArray(detail) && detail.length) {
        return detail
          .map((item) => {
            if (typeof item === 'string') {
              return item.trim();
            }

            if (typeof item?.msg === 'string') {
              return item.msg.trim();
            }

            return '';
          })
          .filter(Boolean)
          .join(' ');
      }

      if (typeof error.error?.message === 'string' && error.error.message.trim()) {
        return error.error.message.trim();
      }
    }

    return fallback;
  }

  private mapEmergencyReportToRequest(report: EmergencyReport): MaintenanceRequest {
    const normalizedReport = this.normalizeEmergencyReport(report);
    const addressParts = [normalizedReport.address?.trim(), normalizedReport.zone?.trim()].filter(Boolean);
    const vehicleLabel = [normalizedReport.vehicle_name?.trim(), normalizedReport.vehicle_plate?.trim()].filter(Boolean).join(' · ');
    const detail =
      normalizedReport.description?.trim() ||
      normalizedReport.problem_type_standardized?.trim() ||
      normalizedReport.problem_type?.trim() ||
      'Emergencia reportada desde la app movil.';

    return {
      id: normalizedReport.id,
      code: `EMG-${String(normalizedReport.id).padStart(6, '0')}`,
      client: normalizedReport.client_name?.trim() || `Cliente #${normalizedReport.client_id ?? normalizedReport.id}`,
      vehicle: vehicleLabel || 'Vehiculo sin detalle',
      location: addressParts.join(' · ') || 'Ubicacion pendiente',
      priority: this.priorityFromProblemType(normalizedReport.problem_type_standardized || normalizedReport.problem_type),
      status: normalizedReport.emergency_status ?? 'pendiente',
      price: normalizedReport.price,
      distance: this.formatDistance(normalizedReport.nearest_workshop_distance_meters),
      detail,
      reportedAt: this.relativeTimeLabel(normalizedReport.created_at),
      createdAt: normalizedReport.created_at,
      latitude: normalizedReport.latitude,
      longitude: normalizedReport.longitude,
      nearestWorkshopId: normalizedReport.nearest_workshop_id,
      nearestWorkshopName: normalizedReport.nearest_workshop_name,
      problemType: normalizedReport.problem_type,
      standardizedProblemType: normalizedReport.problem_type_standardized,
      clientDescription: normalizedReport.description?.trim() || null,
      audioTranscript: normalizedReport.audio_transcript?.trim() || null,
      photoUrls: this.getEmergencyPhotoUrls(normalizedReport),
      audioUrl: this.normalizeBackendAssetUrl(normalizedReport.audio_url),
      mapEmbedUrl: this.buildEmergencyMapEmbedUrl(normalizedReport.latitude, normalizedReport.longitude),
      mapExternalUrl: this.buildEmergencyMapExternalUrl(normalizedReport.latitude, normalizedReport.longitude),
      assignmentId: normalizedReport.assignment_id,
      assignmentStatus: normalizedReport.assignment_status,
      assignedMecanicoId: normalizedReport.assigned_mecanico_id,
      assignedMecanicoName: normalizedReport.assigned_mecanico_name,
      assignedMecanicoPhone: normalizedReport.assigned_mecanico_phone,
      assignedMecanicoSpecialty: normalizedReport.assigned_mecanico_specialty,
    };
  }

  private getEmergencyPhotoUrls(report: EmergencyReport): string[] {
    const rawPhotoUrls = this.parseMediaList(report.photo_urls);
    const rawPhotoPaths = this.parseMediaList(report.photo_paths);
    const normalizedPhotoUrls = rawPhotoUrls
      .map((photoUrl) => this.normalizeBackendAssetUrl(photoUrl))
      .filter((photoUrl): photoUrl is string => Boolean(photoUrl));
    const normalizedPhotoPaths = rawPhotoPaths
      .map((photoPath) => this.normalizeBackendAssetUrl(photoPath))
      .filter((photoUrl): photoUrl is string => Boolean(photoUrl));

    return Array.from(new Set([...normalizedPhotoUrls, ...normalizedPhotoPaths]));
  }

  private parseMediaList(value: string[] | string | null | undefined): string[] {
    if (Array.isArray(value)) {
      return value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim()));
    }

    if (typeof value !== 'string') {
      return [];
    }

    const trimmed = value.trim();

    if (!trimmed) {
      return [];
    }

    try {
      const parsed = JSON.parse(trimmed);

      if (Array.isArray(parsed)) {
        return parsed.filter((item): item is string => typeof item === 'string' && Boolean(item.trim()));
      }
    } catch {
      return [trimmed];
    }

    return [trimmed];
  }

  private buildEmergencyMapEmbedUrl(latitude: number | null, longitude: number | null): SafeResourceUrl | null {
    if (!this.hasValidCoordinates(latitude, longitude)) {
      return null;
    }

    const lat = Number(latitude);
    const lng = Number(longitude);
    const zoomOffset = 0.006;
    const left = lng - zoomOffset;
    const right = lng + zoomOffset;
    const bottom = lat - zoomOffset;
    const top = lat + zoomOffset;
    const url =
      'https://www.openstreetmap.org/export/embed.html' +
      `?bbox=${left}%2C${bottom}%2C${right}%2C${top}` +
      '&layer=mapnik' +
      `&marker=${lat}%2C${lng}`;

    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }

  private buildEmergencyMapExternalUrl(latitude: number | null, longitude: number | null): string | null {
    if (!this.hasValidCoordinates(latitude, longitude)) {
      return null;
    }

    const lat = Number(latitude);
    const lng = Number(longitude);
    return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=16/${lat}/${lng}`;
  }

  private hasValidCoordinates(latitude: number | null, longitude: number | null): boolean {
    return (
      typeof latitude === 'number' &&
      typeof longitude === 'number' &&
      Number.isFinite(latitude) &&
      Number.isFinite(longitude)
    );
  }

  private normalizeBackendAssetUrl(value: string | null | undefined): string | null {
    const normalized = value?.trim();

    if (!normalized) {
      return null;
    }

    if (/^https?:\/\//i.test(normalized)) {
      return normalized;
    }

    if (normalized.startsWith('/')) {
      return `${this.backendBaseUrl}${normalized}`;
    }

    if (normalized.startsWith('uploads/') || normalized.startsWith('emergencias/') || normalized.startsWith('vehicles/')) {
      return `${this.backendBaseUrl}/uploads/${normalized.replace(/^uploads\//, '')}`;
    }

    return `${this.backendBaseUrl}/${normalized}`;
  }

  private priorityFromProblemType(problemType: string | null | undefined): 'Alta' | 'Media' | 'Baja' {
    switch ((problemType || '').trim()) {
      case 'Accidente':
      case 'Motor':
        return 'Alta';
      case 'Batería':
      case 'Neumático':
      case 'Sistema eléctrico':
        return 'Media';
      default:
        return 'Baja';
    }
  }

  private formatDistance(distanceMeters: number | null): string {
    if (distanceMeters === null || Number.isNaN(distanceMeters)) {
      return 'Sin distancia';
    }

    if (distanceMeters < 1000) {
      return `${Math.round(distanceMeters)} m`;
    }

    return `${(distanceMeters / 1000).toFixed(1).replace('.', ',')} km`;
  }

  formatReportPrice(price: number | null): string {
    if (price === null || Number.isNaN(price)) {
      return 'A cotizar';
    }

    return `Bs ${price.toLocaleString('es-BO', { maximumFractionDigits: 0 })}`;
  }

  calculateReportServiceAmount(price: number | null): number | null {
    if (price === null || Number.isNaN(price)) {
      return null;
    }

    return Math.round(price * 0.1);
  }

  calculateReportNetAmount(price: number | null): number | null {
    if (price === null || Number.isNaN(price)) {
      return null;
    }

    return price - this.calculateReportServiceAmount(price)!;
  }

  private relativeTimeLabel(createdAt: string): string {
    const created = new Date(createdAt).getTime();

    if (Number.isNaN(created)) {
      return 'Reciente';
    }

    const diffMinutes = Math.max(1, Math.round((Date.now() - created) / (1000 * 60)));

    if (diffMinutes < 60) {
      return `Hace ${diffMinutes} min`;
    }

    const diffHours = Math.round(diffMinutes / 60);
    if (diffHours < 24) {
      return `Hace ${diffHours} h`;
    }

    const diffDays = Math.round(diffHours / 24);
    return `Hace ${diffDays} d`;
  }

  get selectedMaintenancePhotoUrls(): string[] {
    return this.selectedMaintenanceRequest?.photoUrls ?? [];
  }

  get selectedEmergencyHasCoordinates(): boolean {
    return (
      this.selectedMaintenanceRequest?.latitude !== null &&
      this.selectedMaintenanceRequest?.latitude !== undefined &&
      this.selectedMaintenanceRequest?.longitude !== null &&
      this.selectedMaintenanceRequest?.longitude !== undefined
    );
  }

  private initializeEmergencyMap(element: HTMLDivElement): void {
    if (typeof L === 'undefined') {
      return;
    }

    if (!this.emergencyMap) {
      this.emergencyMap = L.map(element, {
        zoomControl: true,
        scrollWheelZoom: true,
      }).setView([-17.7833, -63.1821], 12);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(this.emergencyMap);

      this.emergencyMapMarkersLayer = L.layerGroup().addTo(this.emergencyMap);
    }

    this.scheduleEmergencyMapResize();
  }

  private initializeSucursalEditMap(element: HTMLDivElement): void {
    if (typeof L === 'undefined') {
      return;
    }

    if (this.sucursalEditMapHost && this.sucursalEditMapHost !== element) {
      this.destroySucursalEditMap();
    }

    this.sucursalEditMapHost = element;

    if (!this.sucursalEditMap) {
      const [latitude, longitude] = this.getSucursalEditCoordinates();

      this.sucursalEditMap = L.map(element, {
        zoomControl: true,
        scrollWheelZoom: true,
      }).setView([latitude, longitude], 13);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(this.sucursalEditMap);

      this.sucursalEditMapMarker = L.marker([latitude, longitude], {
        draggable: true,
      }).addTo(this.sucursalEditMap);

      this.sucursalEditMapMarker.on('dragend', () => {
        const position = this.sucursalEditMapMarker.getLatLng();
        this.updateSucursalEditLocation(position.lat, position.lng);
      });

      this.sucursalEditMap.on('click', (event: { latlng: { lat: number; lng: number } }) => {
        this.updateSucursalEditLocation(event.latlng.lat, event.latlng.lng);
      });
    }

    this.scheduleSucursalEditMapResize();
  }

  private renderSucursalEditMap(animate = false): void {
    if (!this.sucursalEditMap || !this.sucursalEditMapMarker) {
      return;
    }

    const [latitude, longitude] = this.getSucursalEditCoordinates();
    this.sucursalEditMapMarker.setLatLng([latitude, longitude]);
    this.sucursalEditMap.setView([latitude, longitude], 15, { animate });
    this.scheduleSucursalEditMapResize();
  }

  private renderSelectedEmergencyMap(): void {
    if (!this.emergencyMap || !this.emergencyMapMarkersLayer) {
      return;
    }

    this.emergencyMapMarkersLayer.clearLayers();

    const request = this.selectedMaintenanceRequest;

    if (!request || request.latitude === null || request.longitude === null) {
      this.emergencyMap.setView([-17.7833, -63.1821], 12);
      this.scheduleEmergencyMapResize();
      return;
    }

    const bounds: [number, number][] = [];
    const emergencyMarker = L.marker([request.latitude, request.longitude], {
      icon: this.createEmergencyMarkerIcon(),
    }).addTo(this.emergencyMapMarkersLayer);
    emergencyMarker.bindPopup(`
      <strong>${this.escapeHtml(request.code)}</strong><br>
      ${this.escapeHtml(request.client)}<br>
      ${this.escapeHtml(request.location)}
    `);
    bounds.push([request.latitude, request.longitude]);

    const assignedSucursal =
      request.nearestWorkshopId === null
        ? null
        : this.sucursales.find((sucursal) => sucursal.id === request.nearestWorkshopId) ?? null;

    if (
      assignedSucursal &&
      assignedSucursal.latitud !== null &&
      assignedSucursal.longitud !== null
    ) {
      const sucursalMarker = L.marker([assignedSucursal.latitud, assignedSucursal.longitud]).addTo(
        this.emergencyMapMarkersLayer,
      );
      sucursalMarker.bindPopup(`
        <strong>${this.escapeHtml(assignedSucursal.nombre)}</strong><br>
        ${this.escapeHtml(assignedSucursal.direccion)}<br>
        ${this.escapeHtml(assignedSucursal.zona || '')}
      `);

      L.polyline(
        [
          [request.latitude, request.longitude],
          [assignedSucursal.latitud, assignedSucursal.longitud],
        ],
        {
          color: '#1e5aa8',
          weight: 4,
          opacity: 0.8,
          dashArray: '10 8',
        },
      ).addTo(this.emergencyMapMarkersLayer);

      bounds.push([assignedSucursal.latitud, assignedSucursal.longitud]);
    }

    if (bounds.length === 1) {
      this.emergencyMap.setView(bounds[0], 15, { animate: true });
      emergencyMarker.openPopup();
      this.scheduleEmergencyMapResize();
      return;
    }

    this.emergencyMap.fitBounds(bounds, {
      padding: [30, 30],
      maxZoom: 15,
    });
    this.scheduleEmergencyMapResize();
  }

  private createEmergencyMarkerIcon(): any {
    if (typeof L === 'undefined') {
      return undefined;
    }

    return L.divIcon({
      className: 'maintenance-emergency-marker',
      html:
        '<span style="position:relative;display:block;width:26px;height:26px;border-radius:50% 50% 50% 0;background:linear-gradient(180deg,#ff6c63,#d92f2f);border:2px solid rgba(255,255,255,0.96);box-shadow:0 10px 18px rgba(185,31,31,0.28);transform:rotate(-45deg);"><span style="position:absolute;inset:6px;border-radius:50%;background:#fff7f7;"></span></span>',
      iconSize: [26, 38],
      iconAnchor: [13, 38],
      popupAnchor: [0, -34],
    });
  }

  private scheduleEmergencyMapResize(): void {
    if (typeof window === 'undefined' || !this.emergencyMap) {
      return;
    }

    if (this.emergencyMapResizeTimer !== undefined) {
      window.clearTimeout(this.emergencyMapResizeTimer);
    }

    this.emergencyMapResizeTimer = window.setTimeout(() => {
      this.emergencyMap?.invalidateSize();
    }, 120);
  }

  private updateSucursalEditLocation(latitude: number, longitude: number): void {
    this.sucursalForm = {
      ...this.sucursalForm,
      latitud: latitude,
      longitud: longitude,
    };
    this.sucursalLocationMessage = '';

    if (this.sucursalEditMapMarker) {
      this.sucursalEditMapMarker.setLatLng([latitude, longitude]);
    }
  }

  private getSucursalEditCoordinates(): [number, number] {
    const latitude =
      typeof this.sucursalForm.latitud === 'number' && Number.isFinite(this.sucursalForm.latitud)
        ? this.sucursalForm.latitud
        : -17.7833;
    const longitude =
      typeof this.sucursalForm.longitud === 'number' && Number.isFinite(this.sucursalForm.longitud)
        ? this.sucursalForm.longitud
        : -63.1821;

    return [latitude, longitude];
  }

  private scheduleSucursalEditMapResize(): void {
    if (typeof window === 'undefined' || !this.sucursalEditMap) {
      return;
    }

    if (this.sucursalEditMapResizeTimer !== undefined) {
      window.clearTimeout(this.sucursalEditMapResizeTimer);
    }

    this.sucursalEditMapResizeTimer = window.setTimeout(() => {
      this.sucursalEditMap?.invalidateSize();
    }, 120);
  }

  private destroySucursalEditMap(): void {
    if (typeof window !== 'undefined' && this.sucursalEditMapResizeTimer !== undefined) {
      window.clearTimeout(this.sucursalEditMapResizeTimer);
      this.sucursalEditMapResizeTimer = undefined;
    }

    if (this.sucursalEditMap) {
      this.sucursalEditMap.remove();
      this.sucursalEditMap = undefined;
      this.sucursalEditMapMarker = undefined;
    }

    this.sucursalEditMapHost = undefined;
  }

  private escapeHtml(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  get userInitials(): string {
    const parts = this.userDisplayName
      .split(' ')
      .map((part) => part.trim())
      .filter(Boolean)
      .slice(0, 2);

    if (!parts.length) {
      return 'AD';
    }

    return parts.map((part) => part.charAt(0).toUpperCase()).join('');
  }

  get recentSucursales(): Sucursal[] {
    return this.sucursales.slice(0, 4);
  }

  get paginatedSucursales(): Sucursal[] {
    const start = (this.sucursalesPage - 1) * this.sucursalesPageSize;
    return this.sucursales.slice(start, start + this.sucursalesPageSize);
  }

  get sucursalesTotalPages(): number {
    return Math.max(1, Math.ceil(this.sucursales.length / this.sucursalesPageSize));
  }

  get sucursalesRangeStart(): number {
    if (!this.sucursales.length) {
      return 0;
    }

    return (this.sucursalesPage - 1) * this.sucursalesPageSize + 1;
  }

  get sucursalesRangeEnd(): number {
    return Math.min(this.sucursalesPage * this.sucursalesPageSize, this.sucursales.length);
  }

  get recentMecanicos(): Mecanico[] {
    return this.mecanicos.slice(0, 4);
  }

  get filteredMecanicos(): Mecanico[] {
    if (this.mecanicoFilter === 'todos') {
      return this.mecanicos;
    }

    if (this.mecanicoFilter === 'historial') {
      return this.mecanicos.filter((mecanico) => mecanico.status === 'fuera_de_servicio');
    }

    return this.mecanicos.filter((mecanico) => mecanico.status !== 'fuera_de_servicio');
  }

  get hasActiveSucursales(): boolean {
    return this.availableMecanicoSucursales.length > 0;
  }

  get availableMecanicoSucursales(): Sucursal[] {
    if (this.isSecretariaSession && this.currentSecretaria) {
      return this.activeSucursales.filter((sucursal) => sucursal.id === this.currentSecretaria?.sucursal_id);
    }

    return this.activeSucursales;
  }

  get uniqueZonesCount(): number {
    return new Set(this.sucursales.map((sucursal) => sucursal.zona).filter(Boolean)).size;
  }

  get latestSucursalLabel(): string {
    const latest = this.sucursales[0];
    return latest ? latest.nombre : 'Sin registros';
  }

  get latestSucursalDetail(): string {
    const latest = this.sucursales[0];
    return latest
      ? `${latest.responsable || 'Sin responsable'} · ${latest.fecha_registro ? new Date(latest.fecha_registro).toLocaleString() : 'Reciente'}`
      : 'Aun no se ha recibido un nuevo registro operativo.';
  }

  createEmptyMecanicoForm(): MecanicoFormModel {
    return {
      full_name: '',
      phone: '',
      email: '',
      specialty: '',
      status: 'disponible',
      sucursal_id: null,
    };
  }

  createEmptySucursalForm(): SucursalFormModel {
    return {
      nombre: '',
      direccion: '',
      zona: '',
      telefono: '',
      email: '',
      latitud: null,
      longitud: null,
      horario_atencion: '',
      responsable: '',
      estado: 'ACTIVO',
    };
  }

  formatCoordinate(value: number | null): string {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      return '-';
    }

    return value.toFixed(6);
  }

  formatSucursalOptionLabel(sucursal: Sucursal): string {
    return `${sucursal.nombre} · ${sucursal.zona || sucursal.direccion}`;
  }

  createEmptyClientForm(): ClientFormModel {
    return {
      identity_card: '',
      full_name: '',
      email: '',
      phone: '',
      password: '',
      role: 'client',
      status: 'active',
      accepted_terms: true,
    };
  }

  selectSection(section: DashboardSection): void {
    if (!this.canAccessSection(section)) {
      this.selectedSection = this.isWorkshopSession ? 'reports' : 'dashboard';
      return;
    }

    this.selectedSection = section;

    if (section === 'mecanicos') {
      this.loadActiveSucursales();
    }

    if (section === 'secretarias') {
      this.loadSecretarias();
      this.loadActiveSucursales();
    }

    if ((section === 'emergencies' || section === 'reports' || section === 'audit') && !this.maintenanceRequests.length) {
      this.loadEmergencies();
    }

    if (section === 'emergencies') {
      if (typeof window !== 'undefined') {
        window.setTimeout(() => this.renderSelectedEmergencyMap());
      }
    }
  }

  toggleSidebar(): void {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
  }

  logout(): void {
    const confirmed = window.confirm('¿Quieres cerrar sesión?');

    if (!confirmed) {
      return;
    }

    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(this.appSessionStorageKey);
      window.sessionStorage.removeItem(this.appSessionStorageKey);
    }

    void this.router.navigate(['/login']);
  }

  goToPreviousSucursalesPage(): void {
    this.sucursalesPage = Math.max(1, this.sucursalesPage - 1);
  }

  goToNextSucursalesPage(): void {
    this.sucursalesPage = Math.min(this.sucursalesTotalPages, this.sucursalesPage + 1);
  }

  mecanicosByStatus(status: MecanicoStatus): number {
    return this.mecanicos.filter((mecanico) => mecanico.status === status).length;
  }

  statusLabel(status: MecanicoStatus): string {
    if (status === 'fuera_de_servicio') {
      return 'Fuera de servicio';
    }

    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  clientStatusLabel(status: ClientStatus): string {
    return status === 'active' ? 'Activo' : 'Desactivado';
  }

  sucursalStatusLabel(status: WorkshopApprovalStatus): string {
    if (status === 'ACTIVO') {
      return 'Activo';
    }

    return 'Inactivo';
  }

  createEmptySecretariaForm(): SecretariaFormModel {
    return { full_name: '', phone: '', email: '', password: '', sucursal_id: null, status: 'activo' };
  }

  startSecretariaCreate(): void {
    this.editingSecretariaId = null;
    this.secretariaFeedback = '';
    this.secretariaForm = this.createEmptySecretariaForm();
    this.showSecretariaForm = true;
  }

  editSecretaria(secretaria: Secretaria): void {
    this.editingSecretariaId = secretaria.id;
    this.secretariaFeedback = '';
    this.secretariaForm = {
      full_name: secretaria.full_name,
      phone: secretaria.phone || '',
      email: secretaria.email,
      password: '',
      sucursal_id: secretaria.sucursal_id,
      status: secretaria.status,
    };
    this.showSecretariaForm = true;
  }

  cancelSecretariaForm(): void {
    this.showSecretariaForm = false;
    this.editingSecretariaId = null;
    this.secretariaFeedback = '';
    this.secretariaForm = this.createEmptySecretariaForm();
  }

  resetSecretariaForm(): void {
    this.secretariaFeedback = '';
    this.secretariaForm = this.createEmptySecretariaForm();
  }

  submitSecretaria(): void {
    if (!this.secretariaForm.full_name.trim() || !this.secretariaForm.email.trim()) {
      this.secretariaFeedback = 'Nombre y email son obligatorios.';
      return;
    }
    if (!this.editingSecretariaId && !this.secretariaForm.password) {
      this.secretariaFeedback = 'La contraseña es obligatoria al crear.';
      return;
    }
    if (!this.secretariaForm.sucursal_id) {
      this.secretariaFeedback = 'Debe seleccionar una sucursal activa.';
      return;
    }

    this.isSavingSecretaria = true;
    this.secretariaFeedback = '';

    const payload: Record<string, unknown> = {
      full_name: this.secretariaForm.full_name.trim(),
      phone: this.secretariaForm.phone.trim() || null,
      email: this.secretariaForm.email.trim(),
      sucursal_id: this.secretariaForm.sucursal_id,
    };
    if (this.secretariaForm.password) {
      payload['password'] = this.secretariaForm.password;
    }

    const request = this.editingSecretariaId
      ? this.http.put<Secretaria>(`${this.secretariasApiUrl}/${this.editingSecretariaId}`, payload)
      : this.http.post<Secretaria>(this.secretariasApiUrl, payload);

    request.subscribe({
      next: () => {
        this.isSavingSecretaria = false;
        window.alert(this.editingSecretariaId ? 'Secretaria actualizada.' : 'Secretaria registrada.');
        this.cancelSecretariaForm();
        this.loadSecretarias();
      },
      error: (error) => {
        this.isSavingSecretaria = false;
        this.secretariaFeedback = error?.error?.detail || error?.message || 'No se pudo guardar la secretaria.';
      },
    });
  }

  deleteSecretaria(secretaria: Secretaria): void {
    if (!window.confirm(`¿Inactivar a ${secretaria.full_name}?`)) return;
    this.http.delete(`${this.secretariasApiUrl}/${secretaria.id}`).subscribe({
      next: () => {
        window.alert('Secretaria inactivada.');
        this.loadSecretarias();
      },
      error: () => window.alert('No se pudo inactivar la secretaria.'),
    });
  }

  loadSecretarias(): void {
    this.isSecretariasLoading = true;
    this.http.get<Secretaria[]>(this.secretariasApiUrl).subscribe({
      next: (rows) => {
        this.secretarias = rows;
        this.currentSecretaria = this.adminSession
          ? rows.find((secretaria) => secretaria.cliente_id === this.adminSession?.id) ?? null
          : null;
        this.isSecretariasLoading = false;

        if (this.isSecretariaSession) {
          if (this.currentSecretaria) {
            this.mecanicoForm = {
              ...this.mecanicoForm,
              sucursal_id: this.currentSecretaria.sucursal_id,
            };
          }
          this.loadActiveSucursales();
          this.loadMecanicos();
          this.loadEmergencies();
        }
      },
      error: () => {
        this.secretarias = [];
        this.currentSecretaria = null;
        this.isSecretariasLoading = false;
      },
    });
  }

  startSucursalCreate(): void {
    this.editingSucursalId = null;
    this.sucursalEditFeedback = '';
    this.sucursalLocationMessage = '';
    this.sucursalForm = this.createEmptySucursalForm();
    this.showSucursalEditModal = true;
  }

  startCreate(): void {
    this.selectedSection = 'mecanicos';
    this.loadActiveSucursales();
    this.showMecanicoForm = true;
    this.editingMecanicoId = null;
    this.mecanicoFeedback = '';
    this.mecanicoForm = this.createEmptyMecanicoForm();
    if (this.isSecretariaSession && this.currentSecretaria) {
      this.mecanicoForm = {
        ...this.mecanicoForm,
        sucursal_id: this.currentSecretaria.sucursal_id,
      };
    }
  }

  resetMecanicoForm(): void {
    this.editingMecanicoId = null;
    this.mecanicoFeedback = '';
    this.mecanicoForm = this.createEmptyMecanicoForm();
    if (this.isSecretariaSession && this.currentSecretaria) {
      this.mecanicoForm = {
        ...this.mecanicoForm,
        sucursal_id: this.currentSecretaria.sucursal_id,
      };
    }
  }

  cancelMecanicoForm(): void {
    this.showMecanicoForm = false;
    this.resetMecanicoForm();
  }

  editMecanico(mecanico: Mecanico): void {
    this.selectedSection = 'mecanicos';
    this.loadActiveSucursales();
    this.showMecanicoForm = true;
    this.editingMecanicoId = mecanico.id;
    this.mecanicoFeedback = '';
    this.mecanicoForm = {
      full_name: mecanico.full_name,
      phone: mecanico.phone,
      email: mecanico.email,
      specialty: mecanico.specialty,
      status: mecanico.status,
      sucursal_id: this.isSecretariaSession && this.currentSecretaria
        ? this.currentSecretaria.sucursal_id
        : mecanico.sucursal_id,
    };
  }

  submitMecanico(): void {
    const payload = {
      workshop_id: this.currentWorkshopId,
      full_name: this.mecanicoForm.full_name.trim(),
      phone: this.mecanicoForm.phone.trim(),
      email: this.mecanicoForm.email.trim(),
      specialty: this.mecanicoForm.specialty.trim(),
      status: this.mecanicoForm.status,
      sucursal_id: this.isSecretariaSession && this.currentSecretaria
        ? this.currentSecretaria.sucursal_id
        : this.mecanicoForm.sucursal_id,
    };

    if (!payload.full_name || !payload.phone || !payload.email || !payload.specialty) {
      this.mecanicoFeedback = 'Completa todos los campos del mecanico antes de guardar.';
      return;
    }

    if (!this.hasActiveSucursales) {
      this.mecanicoFeedback = 'Debe registrar al menos una sucursal activa antes de crear mecánicos.';
      return;
    }

    if (!payload.sucursal_id) {
      this.mecanicoFeedback = 'Selecciona una sucursal activa para continuar.';
      return;
    }

    this.isSavingMecanico = true;
    this.mecanicoFeedback = '';

    if (this.editingMecanicoId) {
      this.http
        .put<Mecanico>(`${this.mecanicosApiUrl}/${this.editingMecanicoId}`, payload, {
          params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
        })
        .subscribe({
          next: () => {
            this.isSavingMecanico = false;
            this.mecanicoFeedback = 'Mecanico actualizado correctamente.';
            this.resetMecanicoForm();
            this.showMecanicoForm = false;
            this.loadMecanicos();
          },
          error: (error) => {
            this.isSavingMecanico = false;
            this.mecanicoFeedback = this.getApiErrorMessage(error, 'No se pudo actualizar el mecanico.');
          },
        });
      return;
    }

    this.http
      .post<Mecanico>(this.mecanicosApiUrl, payload, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
      })
      .subscribe({
        next: () => {
          this.isSavingMecanico = false;
          this.mecanicoFeedback = 'Mecanico registrado correctamente.';
          this.resetMecanicoForm();
          this.showMecanicoForm = false;
          this.loadMecanicos();
        },
        error: (error) => {
          this.isSavingMecanico = false;
          this.mecanicoFeedback = this.getApiErrorMessage(error, 'No se pudo registrar el mecanico.');
        },
      });
  }

  deleteMecanico(mecanico: Mecanico): void {
    const confirmed = window.confirm(`¿Deseas eliminar a ${mecanico.full_name}?`);

    if (!confirmed) {
      return;
    }

    this.http
      .delete(`${this.mecanicosApiUrl}/${mecanico.id}`, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
      })
      .subscribe({
        next: () => {
          this.mecanicoFeedback = 'Mecanico eliminado correctamente.';
          this.loadMecanicos();
        },
        error: () => {
          this.mecanicoFeedback = 'No se pudo eliminar el mecanico.';
        },
      });
  }

  toggleMecanicoStatus(mecanico: Mecanico): void {
    const nextStatus: MecanicoStatus =
      mecanico.status === 'disponible'
        ? 'ocupado'
        : mecanico.status === 'ocupado'
          ? 'fuera_de_servicio'
          : 'disponible';

    this.http
      .put<Mecanico>(`${this.mecanicosApiUrl}/${mecanico.id}`, {
        workshop_id: mecanico.workshop_id ?? this.currentWorkshopId,
        sucursal_id: mecanico.sucursal_id,
        full_name: mecanico.full_name,
        phone: mecanico.phone,
        email: mecanico.email,
        specialty: mecanico.specialty,
        status: nextStatus,
      }, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
      })
      .subscribe({
        next: () => {
          this.loadMecanicos();
        },
      });
  }

  toggleSucursalStatus(sucursal: Sucursal): void {
    if (this.isUpdatingSucursalStatus) {
      return;
    }

    const nextStatus: WorkshopApprovalStatus = sucursal.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO';

    this.isUpdatingSucursalStatus = true;

    this.sucursalGql.cambiarEstadoSucursal(sucursal.id, nextStatus).subscribe({
      next: () => {
        this.isUpdatingSucursalStatus = false;
        this.loadSucursales();
      },
      error: () => {
        this.isUpdatingSucursalStatus = false;
        window.alert('No se pudo actualizar el estado de la sucursal.');
      },
    });
  }

  editSucursal(sucursal: Sucursal): void {
    this.editingSucursalId = sucursal.id;
    this.sucursalEditFeedback = '';
    this.sucursalLocationMessage = '';
    this.sucursalForm = {
      nombre: sucursal.nombre,
      direccion: sucursal.direccion,
      zona: sucursal.zona || '',
      telefono: sucursal.telefono || '',
      email: sucursal.email || '',
      latitud: sucursal.latitud,
      longitud: sucursal.longitud,
      horario_atencion: sucursal.horario_atencion || '',
      responsable: sucursal.responsable || '',
      estado: sucursal.estado,
    };
    this.showSucursalEditModal = true;
  }

  deleteSucursal(sucursal: Sucursal): void {
    const confirmed = window.confirm(`¿Deseas inactivar la sucursal ${sucursal.nombre}?`);

    if (!confirmed) {
      return;
    }

    this.sucursalGql.eliminarSucursal(sucursal.id).subscribe({
      next: () => {
        window.alert('Sucursal inactivada correctamente.');
        this.loadSucursales();
      },
      error: () => {
        window.alert('No se pudo inactivar la sucursal.');
      },
    });
  }

  cancelSucursalEdit(): void {
    this.showSucursalEditModal = false;
    this.editingSucursalId = null;
    this.isSavingSucursal = false;
    this.sucursalEditFeedback = '';
    this.sucursalLocationMessage = '';
    this.isSucursalLocationLocating = false;
    this.sucursalForm = this.createEmptySucursalForm();
    this.destroySucursalEditMap();
  }

  locateSucursalEditCurrentPosition(): void {
    this.sucursalLocationMessage = '';

    if (!this.isSecureContext) {
      this.sucursalLocationMessage =
        'La ubicación automática del navegador solo funciona en HTTPS o en localhost. Usa el mapa manualmente o abre el sitio con HTTPS.';
      return;
    }

    if (!navigator.geolocation) {
      this.sucursalLocationMessage = 'Tu navegador no soporta geolocalización.';
      return;
    }

    this.isSucursalLocationLocating = true;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        this.updateSucursalEditLocation(position.coords.latitude, position.coords.longitude);
        this.renderSucursalEditMap(true);
        this.isSucursalLocationLocating = false;
      },
      () => {
        this.isSucursalLocationLocating = false;
        this.sucursalLocationMessage =
          'No se pudo obtener tu ubicación actual. Revisa los permisos del navegador.';
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    );
  }

  submitSucursalEdit(): void {
    const payload = {
      nombre: this.sucursalForm.nombre.trim(),
      direccion: this.sucursalForm.direccion.trim(),
      zona: this.sucursalForm.zona.trim() || null,
      telefono: this.sucursalForm.telefono.trim() || null,
      email: this.sucursalForm.email.trim() || null,
      latitud: this.sucursalForm.latitud,
      longitud: this.sucursalForm.longitud,
      horario_atencion: this.sucursalForm.horario_atencion.trim() || null,
      responsable: this.sucursalForm.responsable.trim() || null,
      estado: this.sucursalForm.estado,
    };

    if (
      !payload.nombre ||
      !payload.direccion
    ) {
      this.sucursalEditFeedback = 'Completa el nombre y la dirección de la sucursal.';
      return;
    }

    this.isSavingSucursal = true;
    this.sucursalEditFeedback = '';

    const request = this.editingSucursalId
      ? this.sucursalGql.actualizarSucursal(this.editingSucursalId, payload)
      : this.sucursalGql.crearSucursal(payload);

    request.subscribe({
      next: () => {
        this.isSavingSucursal = false;
        window.alert(this.editingSucursalId ? 'Sucursal actualizada correctamente.' : 'Sucursal registrada correctamente.');
        this.cancelSucursalEdit();
        this.loadSucursales();
      },
      error: (error) => {
        this.isSavingSucursal = false;
        if (error?.status === 401) {
          this.sucursalEditFeedback = 'Tu sesión expiró. Redirigiendo al inicio de sesión...';
        } else {
          this.sucursalEditFeedback =
            error?.message || (this.editingSucursalId ? 'No se pudo actualizar la sucursal.' : 'No se pudo registrar la sucursal.');
        }
      },
    });
  }

  loadSucursales(): void {
    this.isLoading = true;

    this.sucursalGql.listarSucursales().subscribe({
      next: (sucursales) => {
        this.sucursales = sucursales;
        this.sucursalesPage = 1;
        this.isLoading = false;
        this.loadActiveSucursales();
        this.refreshStats();
      },
      error: () => {
        this.sucursales = [];
        this.sucursalesPage = 1;
        this.isLoading = false;
        this.loadActiveSucursales();
        this.refreshStats();
      },
    });
  }

  loadActiveSucursales(): void {
    this.isActiveSucursalesLoading = true;

    this.http
      .get<Sucursal[]>(this.sucursalesApiUrl, {
        params: { estado: 'ACTIVO' },
      })
      .subscribe({
        next: (sucursales) => {
          this.activeSucursales = sucursales;
          this.isActiveSucursalesLoading = false;

          if (
            this.mecanicoForm.sucursal_id !== null &&
            !this.activeSucursales.some((sucursal) => sucursal.id === this.mecanicoForm.sucursal_id)
          ) {
            this.mecanicoForm = {
              ...this.mecanicoForm,
              sucursal_id: null,
            };
          }
        },
        error: () => {
          this.activeSucursales = [];
          this.isActiveSucursalesLoading = false;
        },
      });
  }

  loadMecanicos(): void {
    this.isMecanicosLoading = true;

    this.http
      .get<Mecanico[]>(this.mecanicosApiUrl, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
      })
      .subscribe({
        next: (mecanicos) => {
          this.mecanicos = mecanicos;
          this.isMecanicosLoading = false;
          this.refreshStats();
        },
        error: () => {
          this.mecanicos = [];
          this.isMecanicosLoading = false;
          this.refreshStats();
        },
      });
  }

  private getApiErrorMessage(error: unknown, fallback: string): string {
    if (
      typeof error === 'object' &&
      error !== null &&
      'error' in error &&
      typeof (error as { error?: unknown }).error === 'object' &&
      (error as { error?: { detail?: unknown } }).error !== null
    ) {
      const detail = (error as { error?: { detail?: unknown } }).error?.detail;

      if (typeof detail === 'string' && detail.trim()) {
        return detail;
      }
    }

    return fallback;
  }

  loadClients(): void {
    this.isClientsLoading = true;

    this.http.get<Client[]>(this.clientsApiUrl).subscribe({
      next: (clients) => {
        this.clients = clients;
        this.isClientsLoading = false;
        this.refreshStats();
      },
      error: () => {
        this.clients = [];
        this.isClientsLoading = false;
        this.refreshStats();
      },
    });
  }

  toggleClientStatus(client: Client): void {
    const nextStatus: ClientStatus = client.status === 'active' ? 'suspended' : 'active';

    this.http
      .put<Client>(`${this.clientsApiUrl}/${client.id}/status`, {
        status: nextStatus,
      })
      .subscribe({
        next: () => {
          this.loadClients();
        },
      });
  }

  editClient(client: Client): void {
    this.editingClientId = client.id;
    this.clientEditFeedback = '';
    this.clientForm = {
      identity_card: client.identity_card,
      full_name: client.full_name,
      email: client.email,
      phone: client.phone,
      password: '',
      role: client.role,
      status: client.status,
      accepted_terms: client.accepted_terms,
    };
    this.showClientEditModal = true;
  }

  cancelClientEdit(): void {
    this.showClientEditModal = false;
    this.editingClientId = null;
    this.isSavingClient = false;
    this.clientEditFeedback = '';
    this.clientForm = this.createEmptyClientForm();
  }

  submitClientEdit(): void {
    if (!this.editingClientId) {
      return;
    }

    const payload = {
      identity_card: this.clientForm.identity_card.trim(),
      full_name: this.clientForm.full_name.trim(),
      email: this.clientForm.email.trim(),
      phone: this.clientForm.phone.trim(),
      password: this.clientForm.password.trim(),
      role: this.clientForm.role.trim(),
      status: this.clientForm.status,
      accepted_terms: this.clientForm.accepted_terms,
    };

    if (!payload.identity_card || !payload.full_name || !payload.email || !payload.phone || !payload.role) {
      this.clientEditFeedback = 'Completa carnet, nombre, correo, telefono y rol.';
      return;
    }

    if (payload.password && payload.password.length < 6) {
      this.clientEditFeedback = 'La nueva contraseña debe tener al menos 6 caracteres.';
      return;
    }

    this.isSavingClient = true;
    this.clientEditFeedback = '';

    this.http.put<Client>(`${this.clientsApiUrl}/${this.editingClientId}`, payload).subscribe({
      next: () => {
        this.isSavingClient = false;
        this.cancelClientEdit();
        this.loadClients();
      },
      error: () => {
        this.isSavingClient = false;
        this.clientEditFeedback = 'No se pudo actualizar el cliente.';
      },
    });
  }

  deleteClient(client: Client): void {
    this.clientPendingDelete = client;
    this.showClientDeleteModal = true;
  }

  cancelClientDelete(): void {
    this.showClientDeleteModal = false;
    this.clientPendingDelete = null;
  }

  confirmClientDelete(): void {
    if (!this.clientPendingDelete) {
      return;
    }

    this.http.delete(`${this.clientsApiUrl}/${this.clientPendingDelete.id}`).subscribe({
      next: () => {
        this.cancelClientDelete();
        this.loadClients();
      },
      error: () => {
        window.alert('No se pudo eliminar el cliente.');
      },
    });
  }

  private readAdminSession(): AppSession | null {
    if (typeof window === 'undefined') {
      return null;
    }

    const raw =
      window.localStorage.getItem(this.appSessionStorageKey) ||
      window.sessionStorage.getItem(this.appSessionStorageKey);

    if (!raw) {
      return null;
    }

    const session = parseStoredSession(raw);

    if (!session) {
      clearStoredSession();
      return null;
    }

    return session;
  }

  private refreshStats(): void {
    this.stats = this.stats.map((stat) => {
      if (stat.label === 'Sucursales registradas') {
        return {
          ...stat,
          value: String(this.sucursales.length),
          detail: this.sucursales.length
            ? 'Registros recibidos desde el formulario operativo.'
            : 'Aun no se recibieron registros de sucursal.',
        };
      }

      if (stat.label === 'Mecanicos disponibles') {
        return {
          ...stat,
          value: String(this.mecanicosByStatus('disponible')),
          detail: this.mecanicos.length
            ? 'Estado actualizado segun el mecanico registrado en el panel.'
            : 'Aun no se registraron mecanicos en el sistema.',
        };
      }

      if (stat.label === 'Clientes activos') {
        const activeClients = this.clients.filter((client) => client.status === 'active').length;
        return {
          ...stat,
          value: String(activeClients),
          detail: this.clients.length
            ? 'Clientes con acceso habilitado para autenticacion movil.'
            : 'Aun no se registraron clientes en el sistema.',
        };
      }

      if (stat.label === 'Cobertura') {
        return {
          ...stat,
          value: `${this.uniqueZonesCount || 0} zonas`,
          detail: this.uniqueZonesCount
            ? 'Cobertura detectada en zonas con alta circulacion y demanda.'
            : 'Sin zonas activas registradas todavia.',
        };
      }

      return stat;
    });
  }
}
