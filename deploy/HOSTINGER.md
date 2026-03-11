# Deploy en Hostinger VPS (KVM)

Guia practica para levantar este proyecto completo en un VPS de Hostinger usando Docker Compose.

Este repositorio despliega:

- `nginx` (entrypoint publico)
- `web` (Flask + Gunicorn)
- `frontend` (build en Docker y servido por Nginx dentro del contenedor)
- `db` (MySQL)
- `bfa-node` (opcional, pero consume recursos)

## 0) VPS recomendado

Minimo funcional (baja carga, sin margen):

- `2 vCPU`, `4-8 GB RAM`, `>= 80 GB` NVMe/SSD.

Recomendado para produccion (con margen y `bfa-node`):

- `4 vCPU`, `8-16 GB RAM`, `>= 120-160 GB` NVMe/SSD.

En Hostinger, esto suele equivaler a un plan tipo `VPS KVM 4` o superior (segun oferta vigente).

## 1) Crear el VPS en Hostinger

En hPanel:

1. Comprar VPS (KVM) con el tamano recomendado.
2. Elegir sistema operativo: **Ubuntu 22.04/24.04** (o Debian 12).
3. Configurar acceso:
   - Preferir **SSH key**.
   - Guardar `IP publica`, usuario (usualmente `root`) y/o credenciales.

Conectarte por SSH desde tu PC:

```bash
ssh root@TU_IP
```

## 2) Seguridad de red (muy importante)

El `docker-compose.yml` del repo expone:

- `80` (nginx) publico
- `8545` (RPC de geth) y `30303` (P2P) por `bfa-node`

Recomendacion:

- Exponer solo `80/443` al publico.
- Bloquear `8545` y `30303` salvo que tengas un motivo real para publicarlos.

Firewall (UFW) sugerido:

```bash
apt update && apt upgrade -y
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
```

Nota:

- Aunque UFW bloquee, hoy `bfa-node` igual queda publicado a nivel Docker. Lo mas prolijo es quitar/ajustar esos `ports` en `docker-compose.yml` en el server (ver seccion 6).

## 3) Preparar servidor base

```bash
apt install -y ca-certificates curl gnupg lsb-release git
timedatectl set-timezone America/Argentina/Buenos_Aires
```

## 4) Instalar Docker Engine + Compose plugin

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

## 5) Deploy del proyecto

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

## 6) Ajuste recomendado: no publicar puertos de `bfa-node`

Si no necesitas acceso publico a RPC/P2P, en el VPS edita `docker-compose.yml` y cambia `bfa-node` para que no exponga a Internet.

Opcion simple (recomendada): comentar `ports` de `bfa-node`.

Luego aplicar:

```bash
docker compose --env-file .env up -d --build
```

## 7) Dominio (DNS)

En tu registrador/DNS:

- Registro `A` -> `TU_IP`
- Opcional: `www` (CNAME a raiz o `A` a la misma IP)

## 8) HTTPS (2 opciones)

### Opcion A (simple): Cloudflare como proxy

1. Poner el dominio en Cloudflare.
2. SSL/TLS: modo "Full (strict)".
3. Crear un Origin Certificate y montarlo en tu Nginx (requiere editar `nginx/default.conf` y el compose).

Ventaja: evita pelearte con `certbot` + renovaciones.

### Opcion B (Lets Encrypt): certbot en el host + Nginx en contenedor

Idea: emitir certificados en el host y montar `/etc/letsencrypt` dentro del contenedor `nginx`.

1. Instalar certbot:

```bash
apt update
apt install -y certbot
```

2. Detener temporalmente el contenedor que usa el puerto 80:

```bash
docker stop historia_nginx
```

3. Emitir certificado con modo standalone:

```bash
certbot certonly --standalone -d tu-dominio.com -d www.tu-dominio.com
```

4. Editar `docker-compose.yml` en el VPS:

- En servicio `nginx`, agregar puerto `443:443`
- Montar `/etc/letsencrypt:/etc/letsencrypt:ro`

5. En `nginx/default.conf`:

- Cambiar `server_name` por tu dominio
- Descomentar el bloque HTTPS y ajustar el dominio en rutas de certificado

6. Levantar todo:

```bash
docker compose --env-file .env up -d --build
```

Renovacion:

- Configurar un cron/systemd timer en el host para `certbot renew` y reiniciar `historia_nginx` si renueva.

## 9) Operacion diaria

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

## 10) Backups

Recomendado:

- Snapshot del VPS antes de upgrades grandes (si el proveedor lo soporta).
- Backup logico de MySQL diario (ver scripts en `deploy/templates`).
- Copia externa cifrada de dumps.

## 11) Referencias

- Docker en Ubuntu: https://docs.docker.com/engine/install/ubuntu/
