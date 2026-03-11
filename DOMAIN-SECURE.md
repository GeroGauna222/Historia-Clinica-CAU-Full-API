# DOMAIN + SECURITY RUNBOOK (PRODUCCION)

Guia completa para comprar dominio, apuntarlo al VPS, activar HTTPS, endurecer cookies/sesiones y dejar este proyecto listo para salir a internet de forma segura.

Este runbook asume este stack:

- `docker compose`
- `nginx` como entrypoint publico
- `web` (Flask) y `frontend` internos
- `production.env` como archivo de entorno

---

## 1. Comprar el dominio (registrador)

Usa cualquier registrador serio (DonWeb, Namecheap, Cloudflare Registrar, NIC.ar, etc). Criterios:

- Renovacion anual clara (sin "precio gancho" oculto).
- Panel DNS estable.
- Bloqueo de transferencia (`domain lock`).
- Privacidad WHOIS (si aplica al TLD).
- Soporte para `CAA` records.

Recomendacion practica:

- Si vas con marca institucional: define dominio principal (ej. `historia-cau.unsam.edu.ar`).
- Si compras uno nuevo: usa uno corto y facil de dictar.
- Compra al menos por 2 anos para bajar riesgo operativo.

---

## 2. DNS correcto (zona)

En el DNS del dominio configura:

1. `A` para raiz (`@`) -> `IP_PUBLICA_VPS`
2. `CNAME` para `www` -> `@` (o segundo `A` a la misma IP)
3. `CAA` (opcional pero recomendado) permitiendo `letsencrypt.org`

Ejemplo:

```dns
@      300 IN A     203.0.113.10
www    300 IN CNAME @
@      300 IN CAA   0 issue "letsencrypt.org"
```

Comprobacion:

```bash
nslookup tu-dominio.com
nslookup www.tu-dominio.com
```

Espera propagacion (normal: minutos, maximo: hasta 24-48h).

---

## 3. Preparar `production.env` (secreto y consistente)

Tu archivo `production.env` debe quedar fuera de Git y con secretos reales.

Variables clave:

- `APP_ENV_FILE=production.env`
- `FLASK_ENV=production`
- `FLASK_DEBUG=False`
- `FRONTEND_URL=https://tu-dominio.com`
- `API_URL=https://tu-dominio.com/api`
- `SESSION_COOKIE_SECURE=True`
- `SESSION_COOKIE_SAMESITE=Lax`
- `ENABLE_BLOCKCHAIN_TEST_ENDPOINTS=False`
- `DB_HOST=db`
- `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `MYSQL_ROOT_PASSWORD` fuertes

Permisos recomendados en el VPS:

```bash
chmod 600 production.env
chown root:root production.env
```

Importante:

- Rota secretos si alguna vez estuvieron expuestos en chats, commits o capturas.
- Nunca pases `production.env` al contenedor `frontend`.

---

## 4. Firewall minimo (VPS + proveedor)

Abrir solo:

- `22/tcp` (idealmente restringido a tu IP)
- `80/tcp`
- `443/tcp`

Cerrar/publicar NO:

- `5000` (Flask)
- `3306` (MySQL)
- `8545` (RPC BFA)
- `30303` solo si de verdad necesitas P2P externo

---

## 5. Ajustes de `docker-compose.yml` para HTTPS

En servicio `nginx`:

1. Exponer `443:443`
2. Montar certificados de Lets Encrypt en modo solo lectura

Snippet:

```yaml
nginx:
  image: nginx:latest
  container_name: historia_nginx
  restart: always
  depends_on:
    - web
    - frontend
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
    - uploads_data:/var/www/uploads
    - /etc/letsencrypt:/etc/letsencrypt:ro
  networks:
    - historia_net
```

---

## 6. Nginx seguro (HTTP -> HTTPS + proxy correcto)

Configura dos bloques:

1. Puerto `80`: redireccion a HTTPS (excepto challenge ACME)
2. Puerto `443`: certificados y proxys a `web` y `frontend`

Ejemplo base:

```nginx
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com www.tu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 20M;

    location /uploads/ {
        alias /var/www/uploads/;
        autoindex off;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /api/ {
        proxy_pass http://web:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Nota: `ProxyFix` ya debe estar activo en Flask para respetar `X-Forwarded-Proto`.

---

## 7. Emitir certificado Lets Encrypt

Metodo simple con `standalone`:

1. Instalar certbot en host
2. Parar temporalmente nginx container
3. Emitir cert
4. Volver a levantar stack

```bash
apt update && apt install -y certbot
docker stop historia_nginx
certbot certonly --standalone -d tu-dominio.com -d www.tu-dominio.com
docker compose --env-file production.env up -d --build
```

---

## 8. Renovacion automatica de certificado

Prueba primero:

```bash
certbot renew --dry-run
```

Cron recomendado:

```cron
0 3 * * * certbot renew --quiet && docker restart historia_nginx
```

---

## 9. Levantar produccion (comando canonico)

Desde raiz del repo:

```bash
docker compose --env-file production.env config
docker compose --env-file production.env up -d --build
docker ps
```

Checks rapidos:

```bash
curl -I http://localhost/api/health/public
curl -I https://tu-dominio.com/api/health/public
curl -I https://tu-dominio.com
```

---

## 10. Cookies y sesiones (decision recomendada)

Para este proyecto (frontend y API bajo mismo dominio):

- `SESSION_COOKIE_SECURE=True`
- `SESSION_COOKIE_SAMESITE=Lax`
- mantener autenticacion por cookie de sesion (`Flask-Login`)

Cuando usar `SameSite=None`:

- Solo si frontend y API quedan en sitios distintos (cross-site real).
- En ese caso, `Secure=True` es obligatorio.

---

## 11. Donde guardar secretos en produccion

Nivel recomendado:

1. `production.env` en VPS con permisos `600`
2. Copia cifrada fuera del servidor (password manager o vault)
3. Rotacion trimestral o ante incidente

No recomendado:

- Secretos en repo Git
- Secretos en archivos del frontend
- Enviar llaves por chat/email sin cifrado

---

## 12. Hardening adicional (go-live real)

- Quitar `server_tokens` en nginx.
- Agregar rate limit basico a `/api/login` (si aplica).
- Definir politica de backup y prueba de restore.
- Monitorear expiracion SSL.
- Revisar logs de login y errores 5xx.
- Mantener `ENABLE_BLOCKCHAIN_TEST_ENDPOINTS=False`.

---

## 13. Checklist final (copiar y marcar)

1. Dominio comprado y bloqueado (`domain lock`).
2. DNS (`A`, `www`, `CAA`) propagado.
3. `production.env` completo, con secretos reales y permisos `600`.
4. `docker-compose.yml` con `443:443` y mount de `/etc/letsencrypt`.
5. `nginx/default.conf` con redirect 80->443 y server TLS activo.
6. Certificado emitido para dominio y `www`.
7. Renovacion automatica validada (`dry-run` OK).
8. Salud API responde `200` por HTTPS.
9. Login y flujo principal probados en dominio real.
10. Puertos sensibles no expuestos publicamente.

