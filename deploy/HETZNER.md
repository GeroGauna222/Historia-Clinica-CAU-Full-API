# Deploy en Hetzner Cloud

Guia practica para levantar este proyecto completo en un servidor Hetzner con Docker Compose.

## 0) Arquitectura recomendada

- 1 server Ubuntu (22.04 o 24.04)
- Docker + Docker Compose plugin
- `nginx` (entrypoint publico) + `web` (Flask) + `frontend` + `db` + `bfa-node`
- DNS apuntando a la IP publica del server
- SSL con Let's Encrypt (Certbot)

Para produccion estable, evaluar DB gestionada externa o separar MySQL en otro host.

## 1) Tamano sugerido de servidor

Minimo funcional:

- 2 vCPU
- 4 GB RAM
- 80 GB SSD

Recomendado (con margen por `bfa-node`):

- 4 vCPU
- 8 GB RAM
- 160 GB SSD

## 2) Crear server en Hetzner

En Hetzner Cloud Console:

1. New Project (si no existe)
2. Add Server
3. Image: Ubuntu 22.04 LTS o 24.04 LTS
4. Type: elegir plan segun carga
5. Location: la mas cercana a tus usuarios
6. Authentication: SSH key (evitar password)
7. Activar Backups y Monitoring
8. Crear server

## 3) Firewall en Hetzner Cloud

Crear firewall y asociarlo al server.

Inbound recomendado:

- TCP 22 desde tu IP fija
- TCP 80 desde `0.0.0.0/0` y `::/0`
- TCP 443 desde `0.0.0.0/0` y `::/0`

No exponer publicamente salvo necesidad puntual:

- 5000 (Flask)
- 3306 (MySQL)
- 8545 / 30303 (BFA)

## 4) Preparar servidor base

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg lsb-release git ufw
sudo timedatectl set-timezone America/Argentina/Buenos_Aires
```

Firewall local (opcional adicional):

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 5) Instalar Docker Engine + Compose plugin

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

Crear `.env` en raiz. Minimo:

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

- Registro `A` -> IP publica del server

Certificado:

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

- Activar Backups nativos del server en Hetzner
- Snapshot manual antes de upgrades grandes
- Backup logico de MySQL diario usando tus scripts en `deploy/`
- Copia externa cifrada

## 10) Referencias oficiales

- Hetzner Cloud docs: https://docs.hetzner.com/cloud
- Create server: https://docs.hetzner.com/cloud/servers/getting-started/creating-a-server/
- Firewalls: https://docs.hetzner.com/cloud/firewalls/getting-started/creating-a-firewall/
- Backups: https://docs.hetzner.com/cloud/servers/backups-snapshots/overview/
- Docker en Ubuntu: https://docs.docker.com/engine/install/ubuntu/

