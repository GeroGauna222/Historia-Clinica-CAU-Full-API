# Runbook de despliegue — Historia Clínica CAU

Este documento es el procedimiento operativo oficial para desplegar la aplicación
Flask + Vue 3 + MySQL + Nginx con Docker Compose.

El objetivo es que cada despliegue sea verificable y reversible. No se debe
desplegar desde un árbol de trabajo con cambios locales ni actualizar producción
con un commit que no haya sido revisado y publicado en el repositorio remoto.

## 1. Arquitectura de producción

| Contenedor | Función | Exposición pública |
| --- | --- | --- |
| `edge_gateway` | TLS y reverse proxy compartido | Puertos públicos 80 y 443 |
| `historia_nginx` | Proxy propio de la aplicación | Sólo loopback, puertos 18080 y 18443 |
| `historia_frontend` | Aplicación Vue compilada y servida por Nginx interno | Sólo red Docker |
| `historia_web` | API Flask ejecutada con Gunicorn | Sólo red Docker |
| `historia_db` | MySQL 8 | Sólo red Docker |

La integración con Blockchain Federal Argentina usa su API TSA externa. No existe
un contenedor `bfa-node` en el stack actual.

Los datos persistentes viven en dos volúmenes Docker:

- `db_data`: base MySQL;
- `uploads_data`: adjuntos clínicos.

> **Prohibido en producción:** `docker compose down -v`, `docker volume rm` o
> cualquier variante que elimine volúmenes. Esas operaciones destruyen datos.

## 2. Requisitos

- Servidor Linux con Docker 24 o superior y Docker Compose 2.
- Acceso SSH y permisos para operar Docker.
- Repositorio clonado en el servidor.
- Archivo `.env` de producción fuera de Git y con permisos `600`.
- Certificados válidos en `/etc/letsencrypt/live/cau-hc.com.ar/`.
- Red Docker externa `edge_transport_net` creada y administrada por el proxy compartido.
- Puertos 80 y 443 abiertos para `edge_gateway`; 18080, 18443, 3306 y 5000 deben permanecer privados.
- Commit exacto de la versión aprobado y publicado en `origin`.
- Backup reciente y verificable de la base y de los adjuntos.

### 2.1 Acceso SSH de despliegue

El VPS dispone de una identidad dedicada y revocable. Estos datos no son secretos:

| Campo | Valor |
| --- | --- |
| Alias local | `historia-cau-prod` |
| Host | `66.97.35.134` |
| Puerto | `5858` |
| Usuario | `hcdeploy` |
| Repositorio | `/opt/apps/Historia-Clinica-CAU-Full-API` |
| Clave privada local | `C:\Users\gerog\.ssh\historia_cau_deploy_ed25519` |
| Huella pública | `SHA256:nDM56Ys5qKP4mDrvfi1tUZwbbJkr0S+861WZgNjYxGI` |
| Identificador autorizado | `hcdeploy-codex-2026-09-15` |

La configuración local está en `C:\Users\gerog\.ssh\config`. Con ella, el acceso
no interactivo se verifica mediante:

```bash
ssh -o BatchMode=yes historia-cau-prod "whoami && hostname"
```

La clave privada no debe copiarse al repositorio, al VPS, a tickets ni a mensajes.
`hcdeploy` no tiene contraseña y la clave no permite forwarding. El usuario pertenece
al grupo `docker`, que equivale operativamente a privilegios administrativos; por eso
esta clave debe tratarse como una credencial de producción.

Para revocarla, acceder mediante consola del proveedor u otra identidad administrativa
y eliminar la línea identificada con `hcdeploy-codex-2026-09-15` de:

```text
/home/hcdeploy/.ssh/authorized_keys
```

## 3. Configuración mínima

El `.env` debe incluir, como mínimo:

```dotenv
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<valor-largo-y-aleatorio>
SESSION_COOKIE_SECURE=True
ENABLE_BLOCKCHAIN_TEST_ENDPOINTS=False

MYSQL_ROOT_PASSWORD=<secreto-root-mysql>
DB_HOST=db
DB_USER=hc_app
DB_PASSWORD=<secreto-aplicacion-mysql>
DB_NAME=hc_bfa

VITE_API_URL=/api
FRONTEND_URL=https://cau-hc.com.ar
CORS_ORIGINS=https://cau-hc.com.ar,https://www.cau-hc.com.ar
NGINX_CONF_FILE=./nginx/default.conf
COMPOSE_FILE=docker-compose.yml:/var/backups/historia_cau/config/docker-compose.prod.yml

BFA_TSA_URL=https://tsaapi.bfa.ar/api/tsa
```

Agregar las variables de correo y recetas únicamente cuando esos servicios estén
habilitados. No imprimir ni copiar secretos en logs, tickets o mensajes.

Validar la configuración sin levantar ni recrear servicios:

```bash
chmod 600 .env
docker compose --env-file .env config --quiet
```

Si el comando devuelve un código distinto de cero, detener el despliegue.
Instalar una copia estable del override aprobado fuera del checkout para que siga
disponible incluso al volver a un commit anterior:

```bash
install -d -m 700 /var/backups/historia_cau/config
install -m 600 docker-compose.prod.yml \
  /var/backups/historia_cau/config/docker-compose.prod.yml
```

`COMPOSE_FILE` hace que todos los comandos del runbook combinen la definición base
con ese override estable; no editar `docker-compose.yml` directamente en el VPS.

## 4. Preparación de la versión

Estas verificaciones se ejecutan en el entorno de desarrollo o CI antes de tocar
producción:

```bash
cd backend_flask
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider

cd ../frontend
npm run lint
npm run build
npm audit --omit=dev --audit-level=high
```

Resolver o aceptar explícitamente los hallazgos de seguridad antes de continuar.
Registrar el SHA exacto que se desplegará:

```bash
git status --porcelain
git rev-parse HEAD
```

`git status --porcelain` debe quedar vacío. El commit debe existir en `origin`.

## 5. Backup previo al despliegue

El backup debe abarcar la base y los adjuntos del mismo instante operativo. Se
usa una breve ventana de mantenimiento deteniendo el proxy público durante la
captura. El `trap` vuelve a levantar Nginx aunque falle algún paso.

Desde la raíz del repositorio en producción:

```bash
(
  set -euo pipefail
  umask 077
  RELEASE_TS="$(date +%Y%m%d_%H%M%S)"
  BACKUP_DIR="/var/backups/historia_cau/releases/$RELEASE_TS"
  mkdir -p "$BACKUP_DIR"

  docker stop historia_nginx > /dev/null
  trap 'docker start historia_nginx > /dev/null' EXIT

  docker exec historia_db sh -c \
    'exec mysqldump --single-transaction --routines --triggers -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' \
    | gzip > "$BACKUP_DIR/database.sql.gz"

  docker exec historia_web \
    tar -czf - -C /app/uploads . > "$BACKUP_DIR/uploads.tar.gz"

  gzip -t "$BACKUP_DIR/database.sql.gz"
  tar -tzf "$BACKUP_DIR/uploads.tar.gz" > /dev/null
  test -s "$BACKUP_DIR/database.sql.gz"
  test -s "$BACKUP_DIR/uploads.tar.gz"

  docker start historia_nginx > /dev/null
  trap - EXIT
  printf 'Backup verificado: %s\n' "$BACKUP_DIR"
)
```

Además del backup local, mantener una copia externa o un snapshot del proveedor.
No continuar si alguna validación falla.

## 6. Preflight de la base de datos

La migración `20260915_integridad_borrado_rectificaciones.sql` agrega una restricción
única sobre las versiones rectificadas. Si ya existen duplicados, la migración se
detendrá deliberadamente para no consolidar datos ambiguos.

Ejecutar:

```bash
docker compose --env-file .env exec -T db sh -c \
  'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
    SELECT padre_id, version, COUNT(*) AS cantidad
    FROM evoluciones
    WHERE padre_id IS NOT NULL
    GROUP BY padre_id, version
    HAVING COUNT(*) > 1;
  "'
```

El resultado debe contener sólo los encabezados o estar vacío. Si aparecen filas,
**detener el despliegue** y rectificar esos datos con revisión clínica y de auditoría;
no borrar ni renumerar evoluciones automáticamente.

Comprobar también el estado general del stack:

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=100 web db nginx
curl --fail --silent --show-error https://cau-hc.com.ar/api/health/public
```

## 7. Despliegue de una actualización

Definir el commit aprobado. No usar una rama o etiqueta móvil como evidencia de la
versión:

```bash
cd /opt/apps/Historia-Clinica-CAU-Full-API
RELEASE_COMMIT="REEMPLAZAR_POR_SHA_APROBADO"
PREVIOUS_RELEASE="$(git rev-parse HEAD)"

test "$RELEASE_COMMIT" != "REEMPLAZAR_POR_SHA_APROBADO"
test -z "$(git status --porcelain)"
git fetch --prune origin
git cat-file -e "$RELEASE_COMMIT^{commit}"
git merge-base --is-ancestor "$RELEASE_COMMIT" origin/main
printf '%s\n' "$PREVIOUS_RELEASE" > /var/backups/historia_cau/previous-release.txt
git checkout main
git merge --ff-only "$RELEASE_COMMIT"
test "$(git rev-parse HEAD)" = "$RELEASE_COMMIT"
install -m 600 docker-compose.prod.yml \
  /var/backups/historia_cau/config/docker-compose.prod.yml
```

Si el árbol no está limpio, el commit no existe o el avance no es fast-forward,
detenerse. No usar `git reset --hard` para ocultar el problema.

Construir primero y recrear sólo lo necesario:

```bash
docker compose --env-file .env build --pull
docker compose --env-file .env up -d
```

No es necesario ejecutar `npm run build` en el host: `frontend/Dockerfile` usa
`npm ci` y compila Vue dentro de la imagen.

Al iniciar, `historia_web` ejecuta `/app/start.sh`, que aplica en orden las
migraciones pendientes de `db/migrations/` antes de arrancar Gunicorn. Si una
migración falla, la API no debe considerarse desplegada.

## 8. Verificación posterior

### 8.1 Contenedores, migración y salud

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=200 web

docker compose --env-file .env exec -T db sh -c \
  'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
    SELECT filename, applied_at
    FROM schema_migrations
    WHERE filename = '\''20260915_integridad_borrado_rectificaciones.sql'\'';
  "'

curl --fail --silent --show-error https://cau-hc.com.ar/api/health/public
```

Resultado esperado del health check:

```json
{"status":"ok"}
```

La migración debe figurar en `schema_migrations` y no debe haber reinicios
continuos en `historia_web`.

### 8.2 Smoke test funcional

Realizar con usuarios de prueba autorizados:

1. Iniciar y cerrar sesión.
2. Confirmar que un profesional con tipo y número de matrícula cargados puede crear
   una evolución.
3. Adjuntar un PDF o una imagen válidos y descargarlo.
4. Confirmar que HTML y SVG se rechazan.
5. Rectificar una evolución y comprobar que la versión anterior queda inactiva.
6. Verificar que no se puede eliminar un paciente con documentación clínica.
7. Revisar logs sin exponer datos clínicos ni credenciales.

Monitorear durante la primera hora errores HTTP, reinicios, latencia, espacio en
disco y conexiones MySQL.

## 9. Rollback

### 9.1 Rollback de aplicación

Las restricciones introducidas por la migración de integridad son compatibles con
la versión anterior. Ante un fallo funcional, volver primero sólo el código y
conservar la base:

```bash
PREVIOUS_RELEASE="$(cat /var/backups/historia_cau/previous-release.txt)"
git cat-file -e "$PREVIOUS_RELEASE^{commit}"
git checkout --detach "$PREVIOUS_RELEASE"
docker compose --env-file .env build
docker compose --env-file .env up -d
docker compose --env-file .env ps
curl --fail --silent --show-error https://cau-hc.com.ar/api/health/public
```

El estado detached es intencional y temporal. Registrar el incidente antes del
próximo despliegue. No ejecutar `down -v`.

### 9.2 Restauración de datos

Restaurar la base o los adjuntos sólo si hubo corrupción o una migración de datos
irreversible. Una restauración elimina cambios legítimos realizados después del
backup y debe hacerse dentro de una ventana de mantenimiento, restaurando base y
adjuntos del mismo conjunto.

Antes de restaurar:

1. detener escrituras;
2. conservar una copia del estado fallido para análisis;
3. verificar el backup y su fecha;
4. documentar la pérdida de datos esperada;
5. obtener aprobación operativa.

## 10. Instalación inicial

Para un servidor nuevo:

```bash
cd /opt/apps
git clone https://github.com/GeroGauna222/Historia-Clinica-CAU-Full-API.git
cd Historia-Clinica-CAU-Full-API
```

Crear el `.env`, instalar los certificados y validar `nginx/default.conf` antes de
levantar el stack:

```bash
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --build
curl --fail --silent --show-error https://cau-hc.com.ar/api/health/public
```

`db/init.sql` sólo inicializa un volumen MySQL nuevo. En bases existentes, los
cambios se aplican exclusivamente mediante `db/migrations/`.

## 11. Alertas de agenda

La instalación del cron se realiza una sola vez desde la raíz del repositorio:

```bash
sudo bash deploy/templates/install_alertas_system.sh
sudo crontab -l
```

Para inspeccionar destinatarios sin enviar correos:

```bash
docker exec historia_web flask enviar-alertas
```

La ejecución manual de `/usr/local/bin/alertas_turnos_cau.sh` envía correos reales.

## 12. Diagnóstico rápido

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=200 web
docker compose --env-file .env logs --tail=200 nginx
docker compose --env-file .env logs --tail=200 db
docker inspect historia_web --format '{{.RestartCount}}'
```

Condiciones para abortar o hacer rollback:

- migración ausente o fallida;
- API sin respuesta saludable;
- reinicios repetidos de cualquier contenedor;
- errores nuevos de autenticación o autorización;
- pérdida, duplicación o inconsistencia de datos clínicos;
- rechazo inesperado de evoluciones para profesionales con matrícula cargada;
- ejecución inline de un adjunto activo.

## Referencias

- Configuración específica del proveedor: [DONWEB.md](DONWEB.md)
- Operación resumida para agentes: [../docs/agents/operations.md](../docs/agents/operations.md)
