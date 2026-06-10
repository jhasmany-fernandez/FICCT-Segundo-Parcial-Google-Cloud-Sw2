# Kubernetes Basico

## Objetivo

Preparar manifests Kubernetes minimos para ejecutar localmente los servicios principales del proyecto en `kind`, `minikube` o `Docker Desktop Kubernetes`.

## Alcance de esta fase

- namespace del proyecto
- ConfigMap comun
- Secret de ejemplo sin credenciales reales
- Deployment y Service para:
  - postgres
  - backend
  - frontend
  - ms-ia-multimedia
  - rabbitmq
  - minio
  - gateway
  - prometheus
  - grafana

## Importante

- Las imagenes propias usan placeholders:
  - `ficct-backend:local`
  - `ficct-frontend:local`
  - `ficct-ms-ia-multimedia:local`
  - `ficct-gateway:local`
- Antes de ejecutar en un cluster local, esas imagenes deben construirse y cargarse manualmente en el runtime del cluster.
- Los secretos incluidos son solo de ejemplo.
- No hay credenciales reales en este directorio.

## Validacion recomendada

Si `kubectl` esta disponible:

```bash
kubectl apply -f k8s/namespace.yaml --dry-run=client
kubectl apply -f k8s/ --recursive --dry-run=client
```

## Aplicacion sugerida

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ -n ficct-emergencias --recursive
```

## Comandos utiles

```bash
kubectl get pods -n ficct-emergencias
kubectl get svc -n ficct-emergencias
```
