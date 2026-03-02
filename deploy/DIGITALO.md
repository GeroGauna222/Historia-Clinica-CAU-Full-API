# Deploy en DigitalOcean

Guia practica para levantar este proyecto completo en un Droplet con Docker Compose.

## 0) Arquitectura recomendada

- 1 Droplet Ubuntu (22.04 o 24.04)
- Docker + Docker Compose plugin
- `nginx` (entrypoint publico) + `web` (Flask) + `frontend` + `db` + `bfa-node`
- DNS apuntando al Droplet
- SSL con Let's Encrypt (Certbot)

Para produccion estable, evaluar mover MySQL a Managed MySQL de DigitalOcean.

## 1) Tamano sugerido del Droplet

Minimo funcional:

- 2 vCPU
- 4 GB RAM
- 80 GB SSD

Recomendado (con margen por `bfa-node`):

- 4 vCPU
- 8 GB RAM
- 160 GB SSD

## 2) Crear Droplet

En DigitalOcean Console:

1. Create -> Droplets
2. Imagen: Ubuntu 22.04 LTS o 24.04 LTS
3. Elegir plan segun carga
4. Region: la mas cercana a tus usuarios
5. Auth: SSH key (evitar password)
6. Activar Monitoring y Backups
7. Crear Droplet

## 3) Firewall en DigitalOcean

Crear un Cloud Firewall y asociarlo al Droplet.

Reglas inbound recomendadas:

- TCP 22 desde tu IP fija
- TCP 80 desde `0.0.0.0/0` y `::/0`
- TCP 443 desde `0.0.0.0/0` y `::/0`

Reglas a NO exponer publicamente:

- 5000 (Flask)
- 3306 (MySQL)
- 8545 / 30303 (BFA) salvo caso muy justificado

## 4) Preparar servidor base

Conectarte por SSH y ejecutar:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg lsb-release git ufw
sudo timedatectl set-timezone America/Argentina/Buenos_Aires
```

Configurar firewall local (opcional, si usas tambien UFW):

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 5) Instalar Docker Engine + Compose plugin

Usar instalacion oficial de Docker para Ubuntu:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
```

Opcional (no usar sudo con docker):

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 6) Deploy del proyecto

```bash
cd /opt
sudo git clone https://github.com/Hector-venero/Historia-Clinica-CAU-Full-API.git
sudo chown -R $USER:$USER Historia-Clinica-CAU-Full-API
cd Historia-Clinica-CAU-Full-API
```

Crear `.env` en la raiz (no commitear). Minimo:

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

## 7) Dominio y SSL

DNS:

- Registro `A` -> IP publica del Droplet

Instalar Certbot y emitir certificado:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

## 8) Operacion diaria

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

Rollback rapido:

- volver a commit/tag anterior
- reconstruir con `docker compose ... up -d --build`

## 9) Backups recomendados

- Habilitar Backups del Droplet en DigitalOcean
- Snapshot manual antes de cambios grandes
- Backup logico MySQL diario (ya tenes base de scripts en `deploy/`)
- Copia externa cifrada de dumps

## 10) Referencias oficiales

- Droplet quickstart: https://docs.digitalocean.com/products/droplets/getting-started/quickstart/
- Cloud Firewalls: https://docs.digitalocean.com/docs/networking/firewalls
- Crear Firewalls: https://docs.digitalocean.com/products/networking/firewalls/how-to/create/
- Managed MySQL: https://docs.digitalocean.com/products/databases/mysql/
- Docker en Ubuntu: https://docs.docker.com/engine/install/ubuntu/

