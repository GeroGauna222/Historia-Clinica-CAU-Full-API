# Deploy en DonWeb Cloud Server (Docker / Compose)

Guia practica para levantar este proyecto completo en un Cloud Server de DonWeb usando Docker Compose.

Este repositorio despliega:

- `nginx` (entrypoint publico)
- `web` (Flask + Gunicorn)
- `frontend` (build en Docker y servido por Nginx dentro del contenedor)
- `db` (MySQL)
- `bfa-node` (opcional, pero consume recursos)

## 0) Cloud recomendado

Minimo funcional (baja carga, sin margen):

- `2 vCPU`, `4-8 GB RAM`, `>= 80 GB` SSD/NVMe.

Recomendado para produccion (con margen y `bfa-node`):

- `4 vCPU`, `8-16 GB RAM`, `>= 120-160 GB` SSD/NVMe.

## 0.1) Valores para el formulario de DonWeb

Si te pide estos campos al crear el Cloud Server, usa:

- `vCPUs`: `4`
- `RAM`: `8 GB` (subir a `16 GB` si esperas carga alta)
- `Almacenamiento`: `160 GB` SSD/NVMe (minimo recomendado: `120 GB`)
- `Backup`: `Si` (diario, retencion minima de 7 dias)
- `Transferencia Mensual (TBs)`: `5 TB` (minimo razonable: `3 TB`)
- `Licencias (Paneles y Windows Server RDS SWL Server)`: `Ninguna`
- `Certificado SSL`: `No comprar` al inicio (usar Let's Encrypt)

## 1) Crear Cloud Server en DonWeb

En el Area de Clientes:

1. Comprar/crear un Cloud Server.
2. Elegir imagen: **Ubuntu 24.04** o **Ubuntu 22.04** (o Debian 12).
3. Opcion recomendable: usar una imagen con **Docker** preinstalado si esta disponible en el Marketplace de DonWeb.

Obtener los datos de acceso (IP, usuario/puerto SSH, etc.) desde "Software y Accesos".

## 2) Configurar Firewall Virtual (DonWeb)

DonWeb agrega un **Firewall Virtual** por delante del Cloud Server con politica por defecto "Drop" (bloquea todo inbound). Desde el Area de Cliente tenes que crear reglas para abrir puertos.

Reglas inbound recomendadas:

- TCP `SSH` (puerto segun te indique DonWeb) solo desde tu IP fija (o rango).
- TCP `80` desde `0.0.0.0/0` y `::/0`.
- TCP `443` desde `0.0.0.0/0` y `::/0`.

Reglas a NO exponer publicamente:

- `5000` (Flask)
- `3306` (MySQL)
- `8545` / `30303` (BFA) salvo necesidad real (y aun asi, preferible restringir por IP)

## 3) Acceso por SSH

```bash
ssh root@TU_IP
```

Si DonWeb te asigna un puerto SSH distinto:

```bash
ssh -p PUERTO root@TU_IP
```

## 4) Preparar servidor base

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg lsb-release git ufw
timedatectl set-timezone America/Argentina/Buenos_Aires
```

Firewall a nivel servidor (opcional; el firewall real es el virtual de DonWeb):

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
```

## 5) Instalar Docker + Compose (si no viene preinstalado)

DonWeb ofrece imagen/stack de Docker con Docker Compose preinstalados; si ya lo tenes, saltea esta seccion.

Instalacion oficial para Ubuntu:

```bash
apt update
apt install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
docker --version
docker compose version
```

## 6) Deploy del proyecto

```bash
cd /opt
git clone https://github.com/Hector-venero/Historia-Clinica-CAU-Full-API.git
cd Historia-Clinica-CAU-Full-API
```

Crear `.env` en la raiz del repo (no commitear). Minimo:

```env
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=CAMBIAR_VALOR

DB_HOST=db
DB_USER=hc_app
DB_PASSWORD=CAMBIAR_VALOR
DB_NAME=hc_bfa

VITE_API_URL=/api
FRONTEND_URL=https://tu-dominio.com
```

Levantar stack:

```bash
docker compose --env-file .env up -d --build
docker ps
curl -I http://localhost/api/health/public
```

Acceso sin dominio:

- `http://TU_IP/`

## 7) Hardening recomendado: no publicar puertos de `bfa-node`

Con la configuracion recomendada:

- `8545` queda interno (solo red Docker, no publico).
- `30303` queda expuesto en TCP/UDP para sincronizacion P2P.

Si no necesitas acceso publico a RPC/P2P:

1. En el VPS, edita `docker-compose.yml` y comenta/elimina los `ports:` del servicio `bfa-node`.
2. Reaplica:

```bash
docker compose --env-file .env up -d --build
```

## 8) Dominio (DNS)

En tu DNS/registrador:

- Registro `A` -> IP publica del Cloud Server.

## 9) HTTPS (Lets Encrypt)

Tu Nginx corre dentro de contenedor; el camino mas simple es emitir el cert en el host y montar `/etc/letsencrypt` en el contenedor `nginx`.

1. Instalar certbot:

```bash
apt update
apt install -y certbot
```

2. Parar temporalmente el contenedor que usa el puerto 80:

```bash
docker stop historia_nginx
```

3. Emitir certificado con standalone:

```bash
certbot certonly --standalone -d tu-dominio.com -d www.tu-dominio.com
```

4. Editar `docker-compose.yml` en el VPS:

- En servicio `nginx`, agregar `443:443`
- Montar `/etc/letsencrypt:/etc/letsencrypt:ro`

5. Editar `nginx/default.conf`:

- Cambiar `server_name` a tu dominio
- Descomentar el bloque HTTPS y reemplazar el dominio en las rutas de certificados

6. Levantar todo:

```bash
docker compose --env-file .env up -d --build
```

Renovacion:

- Programar `certbot renew` (cron o systemd timer) y reiniciar `historia_nginx` cuando renueve.

## 10) Operacion diaria

Actualizar:

```bash
cd /opt/Historia-Clinica-CAU-Full-API
git pull
docker compose --env-file .env up -d --build
```

Logs:

```bash
docker compose logs -f web
docker compose logs -f nginx
```

## 11) Checklist pre-go-live

Antes de abrir a usuarios finales, validar:

1. `docker compose --env-file .env config` sin errores.
2. `docker ps` con `historia_nginx`, `historia_web`, `historia_db`, `historia_frontend` y `bfa-node` en estado `Up`.
3. Salud API: `curl -I http://localhost/api/health/public` retorna `200`.
4. Firewall DonWeb:
   - abiertos `22`, `80`, `443`
   - bloqueados `5000`, `3306`, `8545`
   - `30303` abierto solo si realmente necesitas sincronizacion P2P
5. `.env` en produccion:
   - `FLASK_ENV=production`
   - `FLASK_DEBUG=False`
   - `FRONTEND_URL=https://tu-dominio.com`
   - secretos reales para `SECRET_KEY`, `DB_PASSWORD`, `MAIL_PASSWORD`, `PRIVATE_KEY_BFA`
6. Nginx:
   - `server_name` en dominio real
   - HTTPS activo con cert valido
7. Prueba funcional:
   - login correcto
   - alta/edicion de paciente
   - carga de adjunto en `/uploads`
8. Backup:
   - snapshot/backup habilitado en DonWeb
   - prueba de restauracion (al menos 1 vez)

## 12) Referencias

- DonWeb Firewall Cloud Server: https://soporte.donweb.com/hc/es/articles/19364740387348-Cloud-Server-Firewall
- DonWeb Marketplace (Docker): https://marketplace.donweb.com/docker
- DonWeb Docker Hosting Cloud: https://donweb.com/es-int/cloud-docker-hosting
- Docker en Ubuntu: https://docs.docker.com/engine/install/ubuntu/
