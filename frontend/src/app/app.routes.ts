import { Routes } from '@angular/router';

import { authGuard } from './auth.guard';
import { DashboardPageComponent } from './pages/dashboard-page.component';
import { FichaRecepcionDetallePageComponent } from './pages/ficha-recepcion-detalle-page.component';
import { FichaRecepcionFormPageComponent } from './pages/ficha-recepcion-form-page.component';
import { FichasRecepcionPageComponent } from './pages/fichas-recepcion-page.component';
import { ForgotPasswordPageComponent } from './pages/forgot-password-page.component';
import { HomePageComponent } from './pages/home-page.component';
import { LoginPageComponent } from './pages/login-page.component';
import { RecepcionDetallePageComponent } from './pages/recepcion-detalle-page.component';
import { RecepcionDiagnosticoPageComponent } from './pages/recepcion-diagnostico-page.component';
import { RecepcionFormPageComponent } from './pages/recepcion-form-page.component';
import { RecepcionObservacionesPageComponent } from './pages/recepcion-observaciones-page.component';
import { RecepcionesPageComponent } from './pages/recepciones-page.component';
import { MapPageComponent } from './pages/map-page.component';
import { NotFoundPageComponent } from './pages/not-found-page.component';
import { PlanesPageComponent } from './pages/planes-page.component';
import { SectionPageComponent } from './pages/section-page.component';
import { ServiciosPageComponent } from './pages/servicios-page.component';

export const appRoutes: Routes = [
  {
    path: '',
    component: HomePageComponent,
    title: 'Inicio | Automóvil Club Boliviano',
  },
  {
    path: 'suscripciones',
    redirectTo: 'planes',
    pathMatch: 'full',
  },
  {
    path: 'nosotros',
    redirectTo: 'planes',
    pathMatch: 'full',
  },
  {
    path: 'planes',
    component: PlanesPageComponent,
    title: 'Cobertura | Emergencias Vehiculares',
  },
  {
    path: 'novedades',
    redirectTo: 'planes',
    pathMatch: 'full',
  },
  {
    path: 'servicios',
    component: ServiciosPageComponent,
    title: 'Servicios | Asistencia y Auxilio',
  },
  {
    path: 'mapa',
    component: MapPageComponent,
    title: 'Mapa | Santa Cruz de la Sierra',
  },
  {
    path: 'login',
    component: LoginPageComponent,
    title: 'Iniciar sesion | Emergencias Vehiculares',
  },
  {
    path: 'forgot-password',
    component: ForgotPasswordPageComponent,
    title: 'Recuperar contrasena | Emergencias Vehiculares',
  },
  {
    path: 'dashboard',
    component: DashboardPageComponent,
    canActivate: [authGuard],
    title: 'Dashboard | Emergencias Vehiculares',
  },
  {
    path: 'recepciones',
    component: RecepcionesPageComponent,
    canActivate: [authGuard],
    title: 'Recepción de Vehículos | Emergencias Vehiculares',
  },
  {
    path: 'fichas-recepcion',
    component: FichasRecepcionPageComponent,
    canActivate: [authGuard],
    title: 'Fichas de Recepción | Emergencias Vehiculares',
  },
  {
    path: 'fichas-recepcion/nueva',
    component: FichaRecepcionFormPageComponent,
    canActivate: [authGuard],
    title: 'Nueva Ficha de Recepción | Emergencias Vehiculares',
  },
  {
    path: 'fichas-recepcion/:id',
    component: FichaRecepcionDetallePageComponent,
    canActivate: [authGuard],
    title: 'Detalle de Ficha de Recepción | Emergencias Vehiculares',
  },
  {
    path: 'recepciones/nueva',
    component: RecepcionFormPageComponent,
    canActivate: [authGuard],
    title: 'Nueva Recepción | Emergencias Vehiculares',
  },
  {
    path: 'recepciones/:id',
    component: RecepcionDetallePageComponent,
    canActivate: [authGuard],
    title: 'Detalle de Recepción | Emergencias Vehiculares',
  },
  {
    path: 'recepciones/:id/editar',
    component: RecepcionFormPageComponent,
    canActivate: [authGuard],
    title: 'Editar Recepción | Emergencias Vehiculares',
  },
  {
    path: 'recepciones/:id/diagnostico',
    component: RecepcionDiagnosticoPageComponent,
    canActivate: [authGuard],
    title: 'Diagnóstico Mecánico | Emergencias Vehiculares',
  },
  {
    path: 'recepciones/:id/observaciones',
    component: RecepcionObservacionesPageComponent,
    canActivate: [authGuard],
    title: 'Observaciones de Trabajo | Emergencias Vehiculares',
  },
  {
    path: 'escuela',
    redirectTo: 'mapa',
    pathMatch: 'full',
  },
  {
    path: 'contacto',
    component: SectionPageComponent,
    data: { section: 'contacto' },
    title: 'Contacto | Automóvil Club Boliviano',
  },
  {
    path: '**',
    component: NotFoundPageComponent,
    title: 'Página no encontrada',
  },
];
