# 🏥 Historia Clínica CAU – Full API  
**Flask + Vue 3 + MySQL + Docker + Nginx + Blockchain Federal Argentina (BFA)**

Sistema web para la gestión de **historias clínicas unificadas** y **agendas médicas**, desarrollado como **Trabajo Final de Ingeniería en Telecomunicaciones (UNSAM)**.

La solución integra un backend API en Flask, un frontend en Vue 3 (Vite) y persistencia en MySQL, incorporando **auditoría de integridad** mediante hashing y (opcionalmente) sellado/verificación en **BFA** a través de su API oficial de **Timestamp Authority (TSA)**.

---

## ✅ Funcionalidades principales

- **Gestión de pacientes** (alta/edición/búsqueda) y visualización de información clínica.
- **Historias clínicas**: registro, consulta y exportación (según módulo implementado).
- **Turnos**:
  - Agenda por profesional.
  - **Agendas grupales**: turnos asociados a un **grupo profesional** (por especialidad/área).
  - Visualización tipo calendario con **FullCalendar** y listado/gestión.
- **Disponibilidades**: configuración de días y horarios de atención por profesional.
- **Bloqueos de agenda / ausencias**: impedir turnos en fechas específicas.
- **Seguridad**:
  - Autenticación con sesión (Flask-Login).
  - Roles con control de acceso (RBAC) tanto en backend (decoradores) como en frontend (guards).
  - Contraseñas hasheadas (Scrypt/Werkzeug).
  - CORS/CSP configurables (según tu setup).

---

## 👥 Roles del sistema (RBAC)

> Los nombres de roles son los que usás en la app (`director`, `profesional`, `administrativo`, `area`).

- **👑 Director**
  - Gestión completa: usuarios, grupos, auditoría y administración general.
- **👨‍⚕️ Profesional**
  - Manejo de su agenda personal, disponibilidades y acceso a funcionalidades clínicas según permisos.
- **🧾 Administrativo**
  - Operación diaria (pacientes/turnos) con permisos limitados.
- **🏥 Área**
  - Usuario “lógico” que representa una **especialidad/módulo** (ej. *Kinesiología*, *Salud Mental*) para soportar **agendas grupales**.
  - Puede ser miembro de grupos (junto con profesionales) para calendarización y asignación de turnos.

---

## 🧱 Arquitectura

```mermaid
graph TD
  Client[Frontend React/Vite] -->|HTTP| Nginx[Nginx Reverse Proxy]
  Nginx -->|/api| Flask[Backend Flask API]
  Flask --> DB[(MySQL)]
  Flask -->|Opcional| BFA[BFA / Geth]
  Flask -->|Opcional| SMTP[SMTP (recuperación contraseña)]
```

---

## 📦 Estructura del proyecto (resumen)

```bash
historia_clinica_bfa/
├── backend_flask/
│   └── app/
│       ├── routes/              # Endpoints (auth, turnos, grupos, etc.)
│       ├── utils/               # Decoradores permisos, hashing, helpers
│       ├── services/            # Servicios (BFA / lógica)
│       ├── main.py              # Entry Flask
│       └── Dockerfile
├── frontend/                    # Vue 3 + Vite
├── nginx/                       # Reverse proxy
├── db/init.sql                  # Esquema MySQL
└── docker-compose.yml
```

---

## 🚀 Levantar el entorno con Docker

### 1) Clonar

```bash
git clone https://github.com/Hector-venero/Historia-Clinica-CAU-Full-API.git
cd Historia-Clinica-CAU-Full-API
```

### 2) Crear `.env`

```env
# Flask
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=cambia_esto_por_una_clave_segura

# MySQL
DB_HOST=db
DB_USER=hc_app
DB_PASSWORD=cambia_esto
DB_NAME=hc_bfa

# Frontend (si lo usás en CORS / links)
FRONTEND_URL=http://localhost

# Mail (opcional - recuperación de contraseña)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=tu_app_password
MAIL_DEFAULT_SENDER=tu_email@gmail.com

# Blockchain (opcional - BFA TSA API)
BFA_TSA_URL=https://tsaapi.bfa.ar/api/tsa
```

### 3) Build + up

```bash
# Desarrollo (HTTP, sin certificados TLS)
docker compose --env-file .env up -d --build

# Produccion (HTTPS con Let's Encrypt)
docker compose --env-file production.env up -d --build
```

### 4) Acceso

- **Frontend**: `http://localhost`
- **API**: `http://localhost/api`

---

## 🔐 Notas de seguridad recomendadas

- Guardar secretos en `.env` y excluirlos del repo.
- Configurar CORS para permitir solo el dominio del frontend.
- Mantener CSP/HSTS si servís por HTTPS.
- En producción: usar HTTPS real (certificados) y limitar puertos expuestos.

---

## ⛓️ Integridad y Blockchain (BFA TSA API)

El sellado de integridad usa la **API oficial de Timestamp Authority (TSA)** de la BFA (`tsaapi.bfa.ar`), en lugar de un nodo Geth local. Esto elimina el contenedor `bfa-node` y la dependencia de `web3`, bajando drásticamente el consumo de RAM/CPU.

### Flujo de auditoría

1. El sistema genera un **hash SHA-256** del contenido clínico consolidado y lo guarda localmente (`hash_local`).
2. El hash se sella mediante `POST {BFA_TSA_URL}/stamp/`, obteniendo un recibo temporal (`temporary_rd`) que se persiste en la base de datos (`tx_hash`).
3. Para verificar, el sistema consulta `POST {BFA_TSA_URL}/verify/` con el hash actual y el recibo. La respuesta tiene **tres estados**:
   - `success`: el hash está confirmado en la blockchain → integridad válida.
   - `pending`: el sellado existe pero el batch de la TSA aún no subió a la blockchain (puede tardar minutos). **No es una alteración**; se reporta como pendiente y se reintenta más tarde.
   - `failure`: el hash no coincide con lo sellado → posible alteración.
4. En `success`, el recibo definitivo (`permanent_rd`) se decodifica en el backend para mostrar el **número de bloque** y la **fecha/hora de sellado** real en la red.

### Notas de la migración (rama `refactor/bfa-tsa-api`)

- **Infraestructura**: se eliminó el contenedor `bfa-node` del `docker-compose.yml` y la librería `web3` de Python.
- **Backend**: `bfa_client.py` reescrito con `requests` contra `tsaapi.bfa.ar`. La verificación distingue los tres estados de la TSA (`success` / `pending` / `failure`); un sellado `pending` se reporta como pendiente y **nunca** como alterado, evitando el "falso inválido" al verificar inmediatamente después de sellar.
- **Hash exacto**: se sella exactamente el `hash_local` guardado en BD (sin re-aplicar `.strip()`), evitando que el hash sellado difiera del almacenado.
- **Base de datos**: las columnas `tx_hash` y `hash_bfa` se ampliaron a `VARCHAR(512)` para soportar los recibos Base64 extensos de la TSA.

---

## 👤 Autor

**Héctor Venero** – Ingeniería en Telecomunicaciones (UNSAM – ECyT)  
- LinkedIn: https://www.linkedin.com/in/hector-venero-8493a1154/  
- GitHub: https://github.com/Hector-venero  

> “Integridad, interoperabilidad y transparencia médica — Blockchain aplicada a la gestión sanitaria en Argentina.”
