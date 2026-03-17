# Guia de Actualizaciones en Produccion

Esta guia resume un flujo seguro para desplegar mejoras en `cau-hc.com.ar` sin romper el servicio.

## 1) Desarrollar y probar en local

1. Trabaja en una rama nueva.
2. Ejecuta pruebas/lint locales.
3. Merge a `main` solo cuando este estable.

## 2) Backup antes de actualizar

En el VPS:

```bash
cd /opt/apps/Historia-Clinica-CAU-Full-API
cp production.env production.env.bak
MYSQL_ROOT_PASSWORD="$(grep '^MYSQL_ROOT_PASSWORD=' production.env | cut -d= -f2-)"
docker exec historia_db mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" hc_bfa > /root/hc_bfa_$(date +%F_%H%M).sql
```

## 3) Actualizar codigo en VPS

```bash
cd /opt/apps/Historia-Clinica-CAU-Full-API
git pull origin main
```

## 4) Levantar nueva version

```bash
cd /opt/apps/Historia-Clinica-CAU-Full-API
APP_ENV_FILE=production.env docker compose --env-file production.env up -d --build
```

## 5) Verificaciones post-deploy

```bash
docker ps
curl -I https://cau-hc.com.ar
curl -I https://cau-hc.com.ar/api/health/public
docker logs historia_web --tail=100
docker logs historia_nginx --tail=100
```

## 6) Rollback rapido si algo falla

```bash
cd /opt/apps/Historia-Clinica-CAU-Full-API
git log --oneline -n 5
git checkout <commit_anterior_estable>
APP_ENV_FILE=production.env docker compose --env-file production.env up -d --build
```

## 7) Recomendaciones operativas

1. Nunca guardar secretos en Git.
2. Mantener `production.env` fuera de versionado.
3. Probar login y flujo principal despues de cada deploy.
4. Ejecutar periodicamente:

```bash
certbot renew --dry-run
```
