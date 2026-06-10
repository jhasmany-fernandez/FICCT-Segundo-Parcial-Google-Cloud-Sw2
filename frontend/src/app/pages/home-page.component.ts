import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { AfterViewInit, Component, ElementRef, ViewChild, inject } from '@angular/core';
import { FormsModule, NgForm, NgModel } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { RouterLink } from '@angular/router';
import { API_BASE_URL } from '../api-base';
import { AlertSuccessComponent } from './alert-success.component';
import { ValidationDialogComponent } from './validation-dialog.component';

declare const L: any;

type HeroBenefit = {
  title: string;
  description: string;
  icon: string;
};

@Component({
  selector: 'app-home-page',
  standalone: true,
  imports: [AlertSuccessComponent, CommonModule, FormsModule, MatDialogModule, RouterLink],
  template: `
    <main class="home-showcase">
      <section class="hero-banner">
        <div class="hero-overlay"></div>

        <div class="hero-grid">
          <div class="hero-copy">
            <p class="hero-kicker">Red operativa de sucursales propias</p>
            <h1>REGISTRA UNA SUCURSAL DE ATENCION EN LA PLATAFORMA EMPRESARIAL</h1>

            <article class="register-card">
              <p class="card-eyebrow">Alta operativa</p>
              <h2>Registra una sucursal de atencion</h2>
              <p class="card-lead">
                Centraliza la cobertura de tu empresa y habilita atencion de emergencias vehiculares
                desde una sucursal propia.
              </p>

              <form class="register-form" (ngSubmit)="submitWorkshop(workshopForm)" #workshopForm="ngForm">
                <label>
                  <span>Nombre de la Sucursal</span>
                  <input
                    type="text"
                    name="workshopName"
                    [(ngModel)]="form.workshopName"
                    #workshopNameModel="ngModel"
                    placeholder="Nombre de la Sucursal"
                    required
                    minlength="3"
                  />
                  <small class="field-error" *ngIf="showFieldError(workshopNameModel)">
                    Ingresa el nombre de la sucursal.
                  </small>
                </label>

                <label>
                  <span>Nombre Responsable</span>
                  <input
                    type="text"
                    name="contactName"
                    [(ngModel)]="form.contactName"
                    #contactNameModel="ngModel"
                    placeholder="Nombre Responsable"
                    required
                    minlength="3"
                  />
                  <small class="field-error" *ngIf="showFieldError(contactNameModel)">
                    Ingresa el nombre del responsable.
                  </small>
                </label>

                <label>
                  <span>Número Telefónico</span>
                  <input
                    type="tel"
                    name="phone"
                    [(ngModel)]="form.phone"
                    #phoneModel="ngModel"
                    placeholder="Número Telefónico"
                    required
                    minlength="7"
                  />
                  <small class="field-error" *ngIf="showFieldError(phoneModel)">
                    Ingresa un número telefónico válido.
                  </small>
                </label>

                <label>
                  <span>Correo Electrónico</span>
                  <input
                    type="email"
                    name="email"
                    [(ngModel)]="form.email"
                    #emailModel="ngModel"
                    placeholder="Correo Electrónico"
                    required
                  />
                  <small class="field-error" *ngIf="showFieldError(emailModel)">
                    Ingresa un correo electrónico válido.
                  </small>
                </label>

                <label>
                  <span>Zona de la Sucursal</span>
                  <select name="zone" [(ngModel)]="form.zone" #zoneModel="ngModel" required>
                    <option value="">Selecciona una zona</option>
                    <option *ngFor="let zone of workshopZones" [value]="zone">{{ zone }}</option>
                  </select>
                  <small class="field-error" *ngIf="showFieldError(zoneModel)">
                    Selecciona una zona.
                  </small>
                </label>

                <label>
                  <span>Tipo de Especialidades</span>
                  <select name="specialty" [(ngModel)]="form.specialty" #specialtyModel="ngModel" required>
                    <option value="">Selecciona una especialidad</option>
                    <option *ngFor="let specialty of specialties" [value]="specialty">
                      {{ specialty }}
                    </option>
                  </select>
                  <small class="field-error" *ngIf="showFieldError(specialtyModel)">
                    Selecciona una especialidad.
                  </small>
                </label>

                <label class="full-width">
                  <span>Ubicación de la Sucursal</span>
                  <div class="map-field">
                    <button
                      class="map-locate-button"
                      type="button"
                      (click)="locateCurrentPosition()"
                      [disabled]="isLocating"
                      [attr.aria-label]="isLocating ? 'Obteniendo ubicación actual' : 'Usar ubicación actual'"
                      [title]="
                        isLocating
                          ? 'Ubicando...'
                          : isSecureContext
                            ? 'Usar ubicación actual'
                            : 'La ubicación automática requiere HTTPS o localhost'
                      "
                    >
                      ⌖
                    </button>
                    <div
                      #workshopMap
                      class="workshop-map"
                      aria-label="Mapa interactivo de ubicacion de la sucursal"
                    ></div>
                  </div>
                  <div class="map-meta">
                    <small>Haz clic en el mapa o arrastra el marcador para elegir la ubicación exacta.</small>
                    <strong>
                      Lat: {{ selectedLatitude.toFixed(6) }} | Lng: {{ selectedLongitude.toFixed(6) }}
                    </strong>
                    <span class="map-status error" *ngIf="locationMessage">
                      {{ locationMessage }}
                    </span>
                    <span class="map-status error" *ngIf="showLocationError">
                      Selecciona una ubicación en el mapa o usa tu ubicación actual.
                    </span>
                  </div>
                </label>

                <p class="terms-copy">
                  Al registrar la sucursal confirmas la informacion operativa para integrarla al
                  sistema.
                </p>

                <p class="form-feedback error" *ngIf="submitState === 'error'">
                  {{ submitMessage }}
                </p>

                <div class="form-actions">
                  <button
                    class="cta-primary"
                    type="submit"
                    [disabled]="isSubmitting"
                  >
                    {{ isSubmitting ? 'Registrando...' : 'Registrar sucursal' }}
                  </button>
                  <a class="cta-secondary" routerLink="/contacto">Solicitar orientacion</a>
                </div>
              </form>
            </article>
          </div>

          <div class="hero-side">
            <div class="hero-side-copy">
              <p class="hero-intro">
                Gestiona sucursales, cobertura y capacidad tecnica en una sola plataforma empresarial
                orientada a emergencias vehiculares.
              </p>
              <p class="hero-highlight">
                <span>Mas coordinacion,</span>
                <span>mas visibilidad operativa,</span>
                <span class="light">mejor respuesta en campo</span>
              </p>
            </div>

            <div class="mechanic-spotlight" aria-hidden="true">
              <div class="spotlight-halo"></div>
              <div class="mechanic-card">
                <div class="mechanic-tag">Servicio 24/7</div>
                <div class="mechanic-portrait"></div>
              </div>
            </div>

            <aside class="contact-card">
              <p class="contact-kicker">Atención inmediata</p>
              <h2>¿Tienes preguntas? ¡Contáctanos!</h2>

              <a class="contact-action phone" href="tel:800163316">
                <span class="icon">☎</span>
                <span class="contact-text">
                  <strong>800 16 3316</strong>
                  <small>Línea gratuita</small>
                </span>
              </a>

              <a class="contact-action whatsapp" href="https://wa.me/59177795636" target="_blank" rel="noreferrer">
                <span class="icon">W</span>
                <span class="contact-text">
                  <strong>777 95 636</strong>
                  <small>Por WhatsApp</small>
                </span>
              </a>
            </aside>
          </div>
        </div>
      </section>

      <section class="benefits-panel">
        <div class="benefits-head">
          <p class="benefits-kicker">Operacion empresarial conectada</p>
          <h2>Beneficios de una red propia de sucursales</h2>
        </div>

        <div class="benefits-grid">
          <article class="benefit-card" *ngFor="let benefit of benefits">
            <span class="benefit-icon">{{ benefit.icon }}</span>
            <div>
              <h3>{{ benefit.title }}</h3>
              <p>{{ benefit.description }}</p>
            </div>
          </article>
        </div>
      </section>
    </main>

    <app-alert-success
      *ngIf="submitState === 'success'"
      [title]="'Solicitud enviada correctamente'"
      [message]="'La sucursal fue registrada correctamente. El equipo revisara la informacion operativa enviada.'"
    ></app-alert-success>
  `,
  styleUrl: './home-page.component.css',
})
export class HomePageComponent implements AfterViewInit {
  private readonly http = inject(HttpClient);
  private readonly dialog = inject(MatDialog);
  private readonly apiUrl = `${API_BASE_URL}/workshops`;
  private successMessageTimeout?: ReturnType<typeof setTimeout>;
  readonly isSecureContext = window.isSecureContext;

  @ViewChild('workshopMap', { static: true })
  private readonly workshopMapRef?: ElementRef<HTMLDivElement>;

  private mapInstance?: any;
  private mapMarker?: any;

  selectedLatitude = -17.7833;
  selectedLongitude = -63.1821;
  isLocationChosen = false;
  readonly userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  readonly userUtcOffsetMinutes = new Date().getTimezoneOffset() * -1;
  isLocating = false;
  locationMessage = '';
  showLocationError = false;

  readonly form = {
    workshopName: '',
    contactName: '',
    phone: '',
    email: '',
    zone: '',
    specialty: '',
  };

  isSubmitting = false;
  submitState: 'idle' | 'success' | 'error' = 'idle';
  submitMessage = '';

  readonly workshopZones = [
    'zona norte',
    'zona sur',
    'zona este',
    'zona oeste',
    'zona centro',
  ];

  readonly specialties = [
    'Batería',
    'Neumático',
    'Combustible',
    'Motor',
    'Sistema eléctrico',
    'Accidente',
    'Cerrajería / llaves',
  ];

  readonly benefits: HeroBenefit[] = [
    {
      title: 'Cobertura en tiempo real',
      description: 'Coordina solicitudes de asistencia y distribuye la carga operativa entre sucursales.',
      icon: '◉',
    },
    {
      title: 'Acceso a IA avanzada',
      description: 'Diagnóstico rápido automatizado para evaluar emergencias y asignar prioridad.',
      icon: '◎',
    },
    {
      title: 'Visibilidad operativa',
      description: 'Consulta capacidad, ubicacion y especialidad de cada punto de atencion desde una sola vista.',
      icon: '◌',
    },
  ];

  ngAfterViewInit(): void {
    if (!this.workshopMapRef || typeof L === 'undefined') {
      return;
    }

    this.mapInstance = L.map(this.workshopMapRef.nativeElement, {
      center: [this.selectedLatitude, this.selectedLongitude],
      zoom: 13,
      scrollWheelZoom: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(this.mapInstance);

    this.mapMarker = L.marker([this.selectedLatitude, this.selectedLongitude], {
      draggable: true,
    }).addTo(this.mapInstance);

    this.mapMarker.on('dragend', () => {
      const position = this.mapMarker.getLatLng();
      this.updateSelectedLocation(position.lat, position.lng);
    });

    this.mapInstance.on('click', (event: { latlng: { lat: number; lng: number } }) => {
      this.mapMarker.setLatLng(event.latlng);
      this.updateSelectedLocation(event.latlng.lat, event.latlng.lng);
    });
  }

  submitWorkshop(workshopForm: NgForm): void {
    if (this.isSubmitting) {
      return;
    }

    const missingFields = this.getMissingFields(!!workshopForm.invalid);

    if (missingFields.length > 0) {
      this.showLocationError = true;
      this.openValidationDialog(missingFields);
      return;
    }

    this.isSubmitting = true;
    this.submitState = 'idle';
    this.submitMessage = '';

    this.http
      .post(this.apiUrl, {
        workshop_name: this.form.workshopName.trim(),
        contact_name: this.form.contactName.trim(),
        phone: this.form.phone.trim(),
        email: this.form.email.trim(),
        zone: this.form.zone,
        specialty: this.form.specialty,
        latitude: this.selectedLatitude,
        longitude: this.selectedLongitude,
        timezone: this.userTimezone,
        utc_offset_minutes: this.userUtcOffsetMinutes,
      })
      .subscribe({
        next: () => {
          this.isSubmitting = false;
          this.submitState = 'success';
          workshopForm.resetForm({
            workshopName: '',
            contactName: '',
            phone: '',
            email: '',
            zone: '',
            specialty: '',
          });
          this.isLocationChosen = false;
          this.showLocationError = false;
          this.locationMessage = '';
          this.scheduleSuccessMessageHide();
        },
        error: (error: HttpErrorResponse) => {
          this.isSubmitting = false;
          this.submitState = 'error';
          this.submitMessage =
            error.error?.detail || 'No se pudo registrar la sucursal. Verifica el backend e intentalo otra vez.';
        },
      });
  }

  locateCurrentPosition(): void {
    this.locationMessage = '';

    if (!this.isSecureContext) {
      this.locationMessage =
        'La ubicación automática del navegador solo funciona en HTTPS o en localhost. En esta URL usa el mapa manualmente o abre el sitio con HTTPS.';
      return;
    }

    if (!navigator.geolocation) {
      this.locationMessage = 'Tu navegador no soporta geolocalización.';
      return;
    }

    this.isLocating = true;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        this.updateSelectedLocation(latitude, longitude);

        if (this.mapMarker) {
          this.mapMarker.setLatLng([latitude, longitude]);
        }

        if (this.mapInstance) {
          this.mapInstance.setView([latitude, longitude], 16, { animate: true });
        }

        this.isLocating = false;
      },
      () => {
        this.isLocating = false;
        this.locationMessage =
          'No se pudo obtener tu ubicación actual. Revisa los permisos del navegador.';
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    );
  }

  private updateSelectedLocation(latitude: number, longitude: number): void {
    this.selectedLatitude = latitude;
    this.selectedLongitude = longitude;
    this.isLocationChosen = true;
    this.showLocationError = false;
  }

  showFieldError(model: NgModel): boolean {
    return !!model.invalid && (!!model.touched || !!model.dirty);
  }

  private scheduleSuccessMessageHide(): void {
    if (this.successMessageTimeout) {
      clearTimeout(this.successMessageTimeout);
    }

    this.successMessageTimeout = setTimeout(() => {
      this.submitState = 'idle';
    }, 5000);
  }

  private getMissingFields(formInvalid: boolean): string[] {
    const missingFields: string[] = [];

    if (!this.form.workshopName.trim()) {
      missingFields.push('Nombre de la Sucursal');
    }

    if (!this.form.contactName.trim()) {
      missingFields.push('Nombre Responsable');
    }

    if (!this.form.phone.trim() || this.form.phone.trim().length < 7) {
      missingFields.push('Número Telefónico');
    }

    if (!this.form.email.trim() || !this.form.email.includes('@')) {
      missingFields.push('Correo Electrónico');
    }

    if (!this.form.zone) {
      missingFields.push('Zona de la Sucursal');
    }

    if (!this.form.specialty) {
      missingFields.push('Tipo de Especialidades');
    }

    if (!this.isLocationChosen) {
      missingFields.push('Ubicacion de la Sucursal');
    }

    this.showLocationError = !this.isLocationChosen;

    if (!formInvalid && this.isLocationChosen) {
      return [];
    }

    return missingFields;
  }

  private openValidationDialog(missingFields: string[]): void {
    this.dialog.open(ValidationDialogComponent, {
      width: '420px',
      maxWidth: 'calc(100vw - 2rem)',
      data: { missingFields },
    });
  }
}
