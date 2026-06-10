import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

type CustomerService = {
  name: string;
  summary: string;
  cta: string;
  icon: string;
  iconTheme: 'gold' | 'blue';
};

@Component({
  selector: 'app-servicios-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="page">
      <section class="section-hero services-hero">
        <div>
          <p class="eyebrow">Servicios</p>
          <h1>Auxilio vial y asistencia para clientes</h1>
          <p class="lead">
            Soluciones rapidas y efectivas para cualquier emergencia en carretera, con una
            presentacion clara para que clientes y operadores identifiquen la ayuda disponible.
          </p>
        </div>

        <div class="services-hero-card">
          <span>Atencion inmediata</span>
          <strong>Identifica el tipo de asistencia y coordina la respuesta al instante</strong>
          <p>
            Organizamos la asistencia con mensajes cortos, tarjetas visibles y botones directos para
            solicitar apoyo.
          </p>
        </div>
      </section>

      <section class="section services-showcase">
        <div class="services-showcase-head">
          <h2>Nuestros Servicios</h2>
          <p>
            Capacidades de respuesta para incidentes y emergencias vehiculares
          </p>
        </div>

        <div class="customer-services-grid visual-grid">
          <article class="customer-service-card" *ngFor="let service of services">
            <div class="service-icon" [class.gold]="service.iconTheme === 'gold'">
              <span>{{ service.icon }}</span>
            </div>
            <h3>{{ service.name }}</h3>
            <p class="service-summary">{{ service.summary }}</p>
            <a class="button primary service-cta" routerLink="/contacto">{{ service.cta }}</a>
          </article>
        </div>
      </section>
    </main>
  `,
  styleUrl: './shared-pages.css',
})
export class ServiciosPageComponent {
  readonly services: CustomerService[] = [
    {
      name: 'Traslado / Remolque',
      summary: 'Servicio de grua inmediato para cualquier tipo de vehiculo en situaciones de emergencia.',
      cta: 'Solicitar',
      icon: 'GR',
      iconTheme: 'gold',
    },
    {
      name: 'Asistencia Mecanica Vehicular',
      summary: 'Atencion mecanica basica en el lugar para restablecer la movilidad sin necesidad de remolque.',
      cta: 'Solicitar',
      icon: 'AM',
      iconTheme: 'blue',
    },
    {
      name: 'Bateria Descargada',
      summary: 'Servicio de arranque para vehiculos con bateria descargada o cambio de bateria en el lugar.',
      cta: 'Solicitar',
      icon: 'BT',
      iconTheme: 'blue',
    },
    {
      name: 'Falta de Combustible',
      summary: 'Llevamos combustible si el vehiculo quedo inmovilizado por falta de gasolina o diesel.',
      cta: 'Solicitar',
      icon: 'CB',
      iconTheme: 'blue',
    },
    {
      name: 'Cambio de Neumatico',
      summary: 'Apoyo mecanico rapido para reemplazar la llanta y ayudarte a continuar el trayecto.',
      cta: 'Solicitar',
      icon: 'NT',
      iconTheme: 'blue',
    },
    {
      name: 'Otros Servicios',
      summary: 'Diagnostico de averias, cerrajeria vehicular, recarga de aire acondicionado y mas.',
      cta: 'Contactanos',
      icon: 'OT',
      iconTheme: 'blue',
    },
  ];
}
