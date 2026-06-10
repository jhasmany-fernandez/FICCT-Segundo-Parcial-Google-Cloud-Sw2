import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';

import { clearStoredSession, getStoredSession } from './session';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const token = getStoredSession()?.accessToken?.trim();

  const request = !token || req.headers.has('Authorization')
    ? req
    : req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`,
        },
      });

  return next(request).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        clearStoredSession();
        if (router.url !== '/login') {
          router.navigateByUrl('/login');
        }
      }

      return throwError(() => error);
    }),
  );
};
