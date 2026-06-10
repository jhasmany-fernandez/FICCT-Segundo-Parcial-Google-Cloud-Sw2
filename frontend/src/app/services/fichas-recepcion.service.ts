import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../api-base';
import { getStoredSession } from '../session';

export type FichaRecepcionPayload = {
  cliente_id?: number | null;
  emergencia_id?: number | null;
  recibido_por_id?: number | null;
  vehiculo?: string | null;
  placa?: string | null;
  marca?: string | null;
  modelo?: string | null;
  anio?: number | null;
  problema_reportado: string;
  accesorios_recibidos?: string | null;
  observaciones?: string | null;
  assigned_mechanic_id?: number | null;
};

export type FichaRecepcionListItem = {
  id: number;
  cliente_id?: number | null;
  emergencia_id?: number | null;
  codigo_ficha: string;
  estado: string;
  vehiculo: string;
  placa?: string | null;
  problema_reportado: string;
  fecha_ingreso: string;
  assigned_mechanic_id?: number | null;
  assigned_mechanic_name?: string | null;
  created_at: string;
  updated_at: string;
};

export type FichaRecepcionDetail = {
  id: number;
  cliente_id?: number | null;
  emergencia_id?: number | null;
  recibido_por_id?: number | null;
  codigo_ficha: string;
  estado: string;
  vehiculo: string;
  placa?: string | null;
  marca?: string | null;
  modelo?: string | null;
  anio?: number | null;
  problema_reportado: string;
  accesorios_recibidos?: string | null;
  observaciones?: string | null;
  fecha_ingreso: string;
  assigned_mechanic_id?: number | null;
  assigned_mechanic_name?: string | null;
  created_at: string;
  updated_at: string;
};

@Injectable({ providedIn: 'root' })
export class FichasRecepcionService {
  private readonly http = inject(HttpClient);
  private readonly fichasApiUrl = `${API_BASE_URL}/fichas-recepcion`;

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

  listar(): Observable<FichaRecepcionListItem[]> {
    return this.http.get<FichaRecepcionListItem[]>(this.fichasApiUrl, {
      headers: this.getAuthHeaders(),
    });
  }

  crear(payload: FichaRecepcionPayload): Observable<FichaRecepcionDetail> {
    return this.http.post<FichaRecepcionDetail>(this.fichasApiUrl, payload, {
      headers: this.getAuthHeaders(),
    });
  }

  obtener(id: number): Observable<FichaRecepcionDetail> {
    return this.http.get<FichaRecepcionDetail>(`${this.fichasApiUrl}/${id}`, {
      headers: this.getAuthHeaders(),
    });
  }
}
