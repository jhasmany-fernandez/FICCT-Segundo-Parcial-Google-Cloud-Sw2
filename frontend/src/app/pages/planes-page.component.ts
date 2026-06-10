import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

type PlanCard = {
  name: string;
  subtitle?: string;
  description: string;
  benefits: string[];
  badge?: string;
  cta: string;
  theme?: 'highlight' | 'dark';
};

@Component({
  selector: 'app-planes-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="page">
      <section class="section plans-showcase">
        <div class="plans-showcase-top">
          <div class="plans-showcase-copy">
            <h2>Cobertura y capacidad operativa</h2>
            <p>
              Esta vista resume como se organiza el Core empresarial para atender emergencias
              vehiculares en tiempo real.
            </p>
            <p>Mas trazabilidad, mejor coordinacion y una operacion mas clara.</p>
          </div>

          <article class="plans-promo-card">
            <div class="plans-promo-check">✓</div>
            <div>
              <h3>Sin monetizacion ni marketplace</h3>
              <p>La plataforma esta pensada para operar sucursales propias, mecanicos y emergencias.</p>
            </div>
          </article>
        </div>

        <div class="plans-grid">
          <article
            class="plan-card showcase-plan-card"
            *ngFor="let plan of plans"
            [class.plan-highlight]="plan.theme === 'highlight'"
            [class.plan-dark]="plan.theme === 'dark'"
          >
            <span class="plan-badge" *ngIf="plan.badge">{{ plan.badge }}</span>
            <h3>{{ plan.name }}</h3>
            <p class="plan-tagline" *ngIf="plan.subtitle">{{ plan.subtitle }}</p>
            <p class="plan-target" *ngIf="plan.description">{{ plan.description }}</p>

            <ul class="plan-benefits">
              <li *ngFor="let benefit of plan.benefits">{{ benefit }}</li>
            </ul>

            <a class="button primary plan-cta" routerLink="/contacto">{{ plan.cta }}</a>
          </article>
        </div>
      </section>
    </main>
  `,
  styleUrl: './shared-pages.css',
})
export class PlanesPageComponent {
  readonly plans: PlanCard[] = [
    {
      name: 'Cobertura Base',
      badge: 'Operativo',
      description: 'Visibilidad minima para registrar una sucursal y comenzar a coordinar atenciones.',
      benefits: [
        'Registro de sucursal en la plataforma',
        'Visualizacion de capacidad operativa',
        'Recepcion de solicitudes de emergencia',
        'Mapa con ubicacion y especialidad',
        'Seguimiento inicial del punto de atencion',
      ],
      cta: 'Solicitar informacion',
    },
    {
      name: 'Cobertura Coordinada',
      badge: 'Recomendado',
      description: 'Pensado para equipos que requieren mejor distribucion de mecanicos y seguimiento.',
      benefits: [
        'Priorizacion interna de emergencias',
        'Control de mecanicos vehiculares',
        'Vista centralizada de sucursales',
        'Seguimiento de estados operativos',
        'Bitacora mas clara para el equipo',
      ],
      cta: 'Hablar con operaciones',
      theme: 'highlight',
    },
    {
      name: 'Operacion 24/7',
      subtitle: 'Para equipos con disponibilidad continua y necesidad de respuesta inmediata.',
      description: '',
      benefits: [
        'Atencion prioritaria de incidentes criticos',
        'Coordinacion permanente con el panel central',
        'Cobertura extendida por zonas',
        'Mayor trazabilidad de eventos',
        'Seguimiento continuo de emergencias',
        'Preparado para integraciones futuras',
      ],
      cta: 'Coordinar despliegue',
      theme: 'dark',
    },
  ];
}
