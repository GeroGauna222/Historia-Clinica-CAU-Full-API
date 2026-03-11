# Deploy en Alojame Cloud Server

Guia practica para levantar este proyecto completo en Alojame usando Cloud Server con Docker Compose.

## 0) Plan recomendado

Recomendado para este proyecto:

- **Cloud Titanium** (`4 vCPU`, `8 GB RAM`, `50 GB SSD`, `5 TB transferencia`) - **$ 92.000 / mes**.

Importante sobre disco:

- Este repo (con Docker images + MySQL + backups + logs) suele necesitar mas margen.
- Pedir ampliacion de storage al contratar y apuntar a **80 GB minimo** (ideal **120-160 GB**).

Alternativa de entrada (solo baja carga y sin BFA activo):

- **Cloud Business** (`2 vCPU`, `4 GB RAM`, `40 GB SSD`) - **$ 67.000 / mes**.

## 1) Por que este plan

Tu stack de produccion levanta:

- `nginx`
- `web` (Flask + Gunicorn)
- `frontend`
- `db` (MySQL)
- `bfa-node` (si se usa)

Con `bfa-node`, `4 vCPU + 8 GB RAM` reduce riesgo de saturacion inicial.

## 2) Checklist antes de contratar (Alojame)

Pedir confirmacion por escrito de:

- Acceso **root** por SSH.
- SO disponible: **Ubuntu 22.04/24.04** o **Debian 12**.
- Docker Engine + Docker Compose plugin permitidos.
- Posibilidad de aumentar disco sin reinstalar todo.
- Snapshots/backups y procedimiento de recuperacion.

Nota:

- En la pagina de dedicados figura CentOS 7 en planes publicados; no conviene desplegar nuevo entorno sobre CentOS 7.

## 2.1) Pago por transferencia bancaria (requisito)

Alojame lista como medio de pago la **transferencia/dep. bancario**.

Referencia:

- https://alojame.ar/web-hosting-pagos.asp

## 3) Preparar servidor

```bash
ssh root@TU_IP
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg lsb-release git ufw
timedatectl set-timezone America/Argentina/Buenos_Aires
```

Firewall:

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## 4) Instalar Docker + Compose plugin

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
```

## 5) Deploy del proyecto

```bash
cd /opt
git clone https://github.com/Hector-venero/Historia-Clinica-CAU-Full-API.git
cd Historia-Clinica-CAU-Full-API
```

Crear `.env`:

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

Levantar:

```bash
docker compose --env-file .env up -d --build
docker ps
curl -I http://localhost/api/health/public
```

## 6) DNS + SSL

DNS:

- Registro `A` al IP publico del Cloud Server.

SSL:

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

## 7) Operacion diaria

```bash
cd /opt/Historia-Clinica-CAU-Full-API
git pull
docker compose --env-file .env up -d --build
docker compose logs -f web
docker compose logs -f nginx
```

## 8) Referencias

- Alojame Cloud Server: https://alojame.ar/web-hosting-cloud-server.asp
- Alojame Dedicados: https://alojame.ar/web-hosting-servidores-dedicados.asp
- Docker en Ubuntu: https://docs.docker.com/engine/install/ubuntu/
