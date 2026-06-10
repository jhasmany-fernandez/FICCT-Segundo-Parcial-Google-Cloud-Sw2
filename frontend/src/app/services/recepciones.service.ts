import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../api-base';
import { getStoredSession } from '../session';

export type RecepcionStatus = 'registrada' | 'en_diagnostico' | 'en_trabajo' | 'finalizada' | 'entregada';
export type FuelLevel = 'vacio' | '1/4' | '1/2' | '3/4' | 'lleno';
export type ProblemaPriority = 'baja' | 'media' | 'alta';
export type ProblemaReportedBy = 'cliente' | 'secretaria';
export type ObservacionWorkStatus = 'pendiente' | 'en_proceso' | 'pausado' | 'completado';

export type RecepcionClientePayload = {
  full_name: string;
  identity_card: string;
  phone: string;
  email?: string | null;
  address?: string | null;
  mobile_client_id?: number | null;
};

export type RecepcionVehiculoPayload = {
  plate: string;
  brand: string;
  model: string;
  year: number;
  color: string;
  vin?: string | null;
  engine_number?: string | null;
};

export type RecepcionFichaPayload = {
  codigo_ficha?: string | null;
  status?: RecepcionStatus;
  fecha_recepcion?: string | null;
  kilometraje?: number | null;
  nivel_combustible?: FuelLevel | null;
  assigned_mecanico_id?: number | null;
  observaciones_generales?: string | null;
};

export type RecepcionAccesorioPayload = {
  name: string;
  quantity: number;
  notes?: string | null;
};

export type RecepcionProblemaPayload = {
  description: string;
  priority?: ProblemaPriority | null;
  reported_by: ProblemaReportedBy;
};

export type RecepcionPayload = {
  cliente: RecepcionClientePayload;
  vehiculo: RecepcionVehiculoPayload;
  ficha: RecepcionFichaPayload;
  accesorios: RecepcionAccesorioPayload[];
  problemas: RecepcionProblemaPayload[];
};

export type DiagnosticoPayload = {
  diagnostic_text: string;
  estimated_work?: string | null;
  estimated_cost?: number | null;
};

export type ObservacionPayload = {
  observation_text: string;
  work_status?: ObservacionWorkStatus | null;
};

export type RecepcionListFilters = {
  status?: string;
  plate?: string;
  codigo_ficha?: string;
  identity_card?: string;
  assigned_mecanico_id?: number | null;
  limit?: number;
  offset?: number;
};

export type RecepcionListItem = {
  id: number;
  codigo_ficha: string;
  status: RecepcionStatus;
  fecha_recepcion: string;
  client_full_name: string;
  client_identity_card: string;
  client_phone: string;
  client_email?: string | null;
  plate: string;
  vehicle_label: string;
  assigned_mecanico_id?: number | null;
  assigned_mecanico_name?: string | null;
  updated_at: string;
};

export type RecepcionListResponse = {
  items: RecepcionListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type RecepcionAccesorio = {
  id: number;
  ficha_id: number;
  name: string;
  quantity: number;
  notes?: string | null;
};

export type RecepcionProblema = {
  id: number;
  ficha_id: number;
  description: string;
  priority?: ProblemaPriority | null;
  reported_by: ProblemaReportedBy;
  created_at: string;
};

export type RecepcionDiagnostico = {
  id: number;
  ficha_id: number;
  mecanico_id: number;
  diagnostic_text: string;
  estimated_work?: string | null;
  estimated_cost?: number | null;
  created_at: string;
  updated_at: string;
  mecanico_name?: string | null;
};

export type RecepcionObservacion = {
  id: number;
  ficha_id: number;
  mecanico_id: number;
  observation_text: string;
  work_status?: ObservacionWorkStatus | null;
  created_at: string;
  mecanico_name?: string | null;
};

export type RecepcionDetalle = {
  id: number;
  codigo_ficha: string;
  status: RecepcionStatus;
  fecha_recepcion: string;
  cliente: {
    id: number;
    full_name: string;
    identity_card: string;
    phone: string;
    email?: string | null;
    address?: string | null;
    mobile_client_id?: number | null;
  };
  vehiculo: {
    id: number;
    plate: string;
    brand: string;
    model: string;
    year: number;
    color: string;
    vin?: string | null;
    engine_number?: string | null;
  };
  ficha: {
    codigo_ficha: string;
    status: RecepcionStatus;
    fecha_recepcion: string;
    kilometraje?: number | null;
    nivel_combustible?: FuelLevel | null;
    recepcionado_por_user_id: number;
    recepcionado_por_role: string;
    assigned_mecanico_id?: number | null;
    assigned_mecanico_name?: string | null;
    observaciones_generales?: string | null;
    created_at: string;
    updated_at: string;
  };
  accesorios: RecepcionAccesorio[];
  problemas: RecepcionProblema[];
  diagnosticos: RecepcionDiagnostico[];
  observaciones: RecepcionObservacion[];
};

export type RecepcionCreateResponse = {
  id: number;
  codigo_ficha: string;
  status: RecepcionStatus;
  cliente_id: number;
  vehiculo_id: number;
  fecha_recepcion: string;
  assigned_mecanico_id?: number | null;
  created_at: string;
};

export type RecepcionEstado = {
  ficha_id: number;
  codigo_ficha: string;
  status: RecepcionStatus;
  vehicle: string;
  plate: string;
  last_diagnostic?: string | null;
  last_observation?: string | null;
  updated_at: string;
};

export type RecepcionMechanicOption = {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  status: string;
};

type RecepcionLegacyAssignmentAliases = {
  assigned_mecanico_id?: number | null;
  assigned_mecanico_name?: string | null;
  assigned_mecanico_phone?: string | null;
  assigned_mecanico_email?: string | null;
  assigned_mecanico_specialty?: string | null;
  assigned_mechanic_id?: number | null;
  assigned_mechanic_name?: string | null;
  assigned_technician_id?: number | null;
  assigned_technician_name?: string | null;
  assigned_technician_phone?: string | null;
  assigned_technician_email?: string | null;
  assigned_technician_specialty?: string | null;
  mecanico_id?: number | null;
  mecanico_name?: string | null;
  mechanic_id?: number | null;
  mechanic_name?: string | null;
  technician_id?: number | null;
  technician_name?: string | null;
};

type RecepcionListItemResponse = Omit<RecepcionListItem, 'assigned_mecanico_id' | 'assigned_mecanico_name'> &
  RecepcionLegacyAssignmentAliases;

type RecepcionDiagnosticoResponse = Omit<RecepcionDiagnostico, 'mecanico_id' | 'mecanico_name'> &
  RecepcionLegacyAssignmentAliases;

type RecepcionObservacionResponse = Omit<RecepcionObservacion, 'mecanico_id' | 'mecanico_name'> &
  RecepcionLegacyAssignmentAliases;

type RecepcionDetalleResponse = Omit<RecepcionDetalle, 'ficha' | 'diagnosticos' | 'observaciones'> & {
  ficha: Omit<RecepcionDetalle['ficha'], 'assigned_mecanico_id' | 'assigned_mecanico_name'> &
    RecepcionLegacyAssignmentAliases;
  diagnosticos: RecepcionDiagnosticoResponse[];
  observaciones: RecepcionObservacionResponse[];
};

type RecepcionCreateResponseRaw = Omit<RecepcionCreateResponse, 'assigned_mecanico_id'> &
  RecepcionLegacyAssignmentAliases;

@Injectable({ providedIn: 'root' })
export class RecepcionesService {
  private readonly http = inject(HttpClient);
  private readonly recepcionesApiUrl = `${API_BASE_URL}/recepciones`;

  private getAuthHeaders(): HttpHeaders {
    const session = getStoredSession();
    const token = session?.accessToken?.trim();

    if (!token) {
      return new HttpHeaders();
    }

    return new HttpHeaders({
      Authorization: `Bearer ${token}`,
    });
  }

  private buildParams(filters?: RecepcionListFilters): HttpParams {
    let params = new HttpParams();

    if (!filters) {
      return params;
    }

    for (const [key, value] of Object.entries(filters)) {
      if (value === null || value === undefined || value === '') {
        continue;
      }

      const httpKey = key === 'assigned_mecanico_id' ? 'assigned_mechanic_id' : key;
      params = params.set(httpKey, String(value));
    }

    return params;
  }

  listarRecepciones(filters?: RecepcionListFilters): Observable<RecepcionListResponse> {
    return new Observable<RecepcionListResponse>((subscriber) => {
      this.http
        .get<{ items: RecepcionListItemResponse[]; total: number; limit: number; offset: number }>(this.recepcionesApiUrl, {
          headers: this.getAuthHeaders(),
          params: this.buildParams(filters),
        })
        .subscribe({
          next: (response) => {
            subscriber.next({
              ...response,
              items: response.items.map((item) => this.normalizeRecepcionListItem(item)),
            });
            subscriber.complete();
          },
          error: (error) => subscriber.error(error),
        });
    });
  }

  obtenerRecepcion(id: number): Observable<RecepcionDetalle> {
    return new Observable<RecepcionDetalle>((subscriber) => {
      this.http
        .get<RecepcionDetalleResponse>(`${this.recepcionesApiUrl}/${id}`, {
          headers: this.getAuthHeaders(),
        })
        .subscribe({
          next: (response) => {
            subscriber.next(this.normalizeRecepcionDetalle(response));
            subscriber.complete();
          },
          error: (error) => subscriber.error(error),
        });
    });
  }

  crearRecepcion(payload: RecepcionPayload): Observable<RecepcionCreateResponse> {
    return new Observable<RecepcionCreateResponse>((subscriber) => {
      this.http
        .post<RecepcionCreateResponseRaw>(this.recepcionesApiUrl, this.buildRecepcionPayload(payload), {
          headers: this.getAuthHeaders(),
        })
        .subscribe({
          next: (response) => {
            subscriber.next(this.normalizeRecepcionCreateResponse(response));
            subscriber.complete();
          },
          error: (error) => subscriber.error(error),
        });
    });
  }

  actualizarRecepcion(id: number, payload: RecepcionPayload): Observable<RecepcionDetalle> {
    return new Observable<RecepcionDetalle>((subscriber) => {
      this.http
        .put<RecepcionDetalleResponse>(`${this.recepcionesApiUrl}/${id}`, this.buildRecepcionPayload(payload), {
          headers: this.getAuthHeaders(),
        })
        .subscribe({
          next: (response) => {
            subscriber.next(this.normalizeRecepcionDetalle(response));
            subscriber.complete();
          },
          error: (error) => subscriber.error(error),
        });
    });
  }

  obtenerFicha(id: number): Observable<RecepcionDetalle> {
    return new Observable<RecepcionDetalle>((subscriber) => {
      this.http
        .get<RecepcionDetalleResponse>(`${this.recepcionesApiUrl}/${id}/ficha`, {
          headers: this.getAuthHeaders(),
        })
        .subscribe({
          next: (response) => {
            subscriber.next(this.normalizeRecepcionDetalle(response));
            subscriber.complete();
          },
          error: (error) => subscriber.error(error),
        });
    });
  }

  crearDiagnostico(id: number, payload: DiagnosticoPayload): Observable<RecepcionDiagnostico> {
    return new Observable<RecepcionDiagnostico>((subscriber) => {
      this.http
        .post<RecepcionDiagnosticoResponse>(`${this.recepcionesApiUrl}/${id}/diagnostico`, payload, {
          headers: this.getAuthHeaders(),
        })
        .subscribe({
          next: (response) => {
            subscriber.next(this.normalizeRecepcionDiagnostico(response));
            subscriber.complete();
          },
          error: (error) => subscriber.error(error),
        });
    });
  }

  crearObservacion(id: number, payload: ObservacionPayload): Observable<RecepcionObservacion> {
    return new Observable<RecepcionObservacion>((subscriber) => {
      this.http
        .post<RecepcionObservacionResponse>(`${this.recepcionesApiUrl}/${id}/observaciones`, payload, {
          headers: this.getAuthHeaders(),
        })
        .subscribe({
          next: (response) => {
            subscriber.next(this.normalizeRecepcionObservacion(response));
            subscriber.complete();
          },
          error: (error) => subscriber.error(error),
        });
    });
  }

  obtenerEstado(id: number): Observable<RecepcionEstado> {
    return this.http.get<RecepcionEstado>(`${this.recepcionesApiUrl}/${id}/estado`, {
      headers: this.getAuthHeaders(),
    });
  }

  listarMecanicosAsignables(): Observable<RecepcionMechanicOption[]> {
    return this.http.get<RecepcionMechanicOption[]>(`${this.recepcionesApiUrl}/mecanicos-asignables`, {
      headers: this.getAuthHeaders(),
    });
  }

  private getAssignedMecanicoId(item: RecepcionLegacyAssignmentAliases & { assigned_mecanico_id?: number | null }): number | null {
    return (
      item.assigned_mecanico_id ??
      item.assigned_mechanic_id ??
      item.assigned_technician_id ??
      item.mechanic_id ??
      item.technician_id ??
      null
    );
  }

  private getAssignedMecanicoName(
    item: RecepcionLegacyAssignmentAliases & { assigned_mecanico_name?: string | null },
  ): string | null {
    return (
      item.assigned_mecanico_name ??
      item.assigned_mechanic_name ??
      item.assigned_technician_name ??
      item.mechanic_name ??
      item.technician_name ??
      null
    );
  }

  private normalizeRecepcionListItem(item: RecepcionListItemResponse): RecepcionListItem {
    return {
      ...item,
      assigned_mecanico_id: this.getAssignedMecanicoId(item),
      assigned_mecanico_name: this.getAssignedMecanicoName(item),
    };
  }

  private normalizeRecepcionDiagnostico(item: RecepcionDiagnosticoResponse): RecepcionDiagnostico {
    return {
      ...item,
      mecanico_id: item.mecanico_id ?? item.mechanic_id ?? item.technician_id ?? 0,
      mecanico_name: this.getAssignedMecanicoName(item),
    };
  }

  private normalizeRecepcionObservacion(item: RecepcionObservacionResponse): RecepcionObservacion {
    return {
      ...item,
      mecanico_id: item.mecanico_id ?? item.mechanic_id ?? item.technician_id ?? 0,
      mecanico_name: this.getAssignedMecanicoName(item),
    };
  }

  private normalizeRecepcionDetalle(response: RecepcionDetalleResponse): RecepcionDetalle {
    return {
      ...response,
      ficha: {
        ...response.ficha,
        assigned_mecanico_id: this.getAssignedMecanicoId(response.ficha),
        assigned_mecanico_name: this.getAssignedMecanicoName(response.ficha),
      },
      diagnosticos: response.diagnosticos.map((item) => this.normalizeRecepcionDiagnostico(item)),
      observaciones: response.observaciones.map((item) => this.normalizeRecepcionObservacion(item)),
    };
  }

  private normalizeRecepcionCreateResponse(response: RecepcionCreateResponseRaw): RecepcionCreateResponse {
    return {
      ...response,
      assigned_mecanico_id: this.getAssignedMecanicoId(response),
    };
  }

  private buildRecepcionPayload(payload: RecepcionPayload): Omit<RecepcionPayload, 'ficha'> & {
    ficha: RecepcionFichaPayload & { assigned_mechanic_id?: number | null };
  } {
    return {
      ...payload,
      ficha: {
        ...payload.ficha,
        // Backend legacy alias preserved temporarily. Frontend canonical field is mecanico_id.
        assigned_mechanic_id: payload.ficha.assigned_mecanico_id ?? null,
      },
    };
  }
}
