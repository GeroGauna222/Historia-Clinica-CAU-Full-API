# Deploy en Wiroos Cloud

Guia practica para levantar este proyecto completo en Wiroos usando un Cloud Server con Docker Compose.

## 0) Plan recomendado

Recomendado para este proyecto (incluyendo `bfa-node`):

- **Cloud SSD 2020 Gold** (`4 cores`, `8 GB RAM`, `160 GB SSD NVMe`, transferencia ilimitada) - **$ 94.140,00 / mes**.

Alternativa de entrada (si arranca con baja carga y sin BFA activo):

- **Cloud SSD 2020 Silver** (`2 cores`, `4 GB RAM`, `80 GB SSD NVMe`) - **$ 50.690,00 / mes**.

No recomendado para este repositorio:

- Planes de hosting compartido (ej: "Plan Avanzado" con cPanel/LiteSpeed), porque este stack requiere Docker, Compose y control de servidor.

## 1) Por que este plan

Este repo en produccion levanta:

- `nginx` (publico)
- `web` (Flask + Gunicorn)
- `frontend`
- `db` (MySQL)
- `bfa-node` (opcional pero pesado)

Con `bfa-node`, `4 vCPU + 8 GB RAM` es el punto equilibrado para no quedar ajustado desde el inicio.

## 2) Checklist antes de contratar (Wiroos)

Pedir confirmacion por ticket/comercial de:

- Acceso **root** por SSH.
- SO soportado: **Ubuntu 22.04/24.04** o **Debian 12**.
- Sin restriccion para instalar Docker Engine + Docker Compose plugin.
- Apertura de puertos `80/443` y salida a Internet para pull de imagenes.
- Politica de snapshots/backups y tiempos de restore.

## 2.1) Pago por transferencia bancaria (requisito)

Wiroos publica que se puede abonar por **transferencia bancaria o deposito bancario** desde el area de clientes, y que se debe enviar el comprobante al sector de pagos para que se acredite.

Referencia:

- https://clientes.wiroos.com/knowledgebase/43/Es_posible_abonar_por_transferencia_o_depsito_bancario.html

## 3) Preparar el servidor

Conectarte por SSH:

```bash
ssh root@TU_IP
```

Actualizar base:

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg lsb-release git ufw
timedatectl set-timezone America/Argentina/Buenos_Aires
```

Firewall local:

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

Crear `.env` en raiz:

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

## 6) DNS y SSL

DNS:

- Registro `A` -> IP publica del Cloud Server.

SSL:

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

## 7) Operacion diaria

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

## 8) Referencias

- Wiroos cloud (tabla comparativa): https://wiroos.com/argentina/dedicados-tabla-comparativa.html
- Wiroos cloud overview: https://wiroos.com/argentina/dedicados-Cloud_Standard.html
- Docker en Ubuntu: https://docs.docker.com/engine/install/ubuntu/
