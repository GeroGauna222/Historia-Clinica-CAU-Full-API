# Operations and deploy guidelines

## Canonical commands

- Start: `docker compose --env-file .env up -d --build`
- Stop: `docker compose down`
- Check services: `docker ps`
- Health check: `curl -I http://localhost/api/health/public`

## Service expectations

- `nginx` is the only public entrypoint (`80`).
- Backend Flask container is internal and proxied by nginx under `/api/`.
- Frontend build is produced inside Docker image (`frontend/Dockerfile`).
- MySQL schema bootstrap is controlled by `db/init.sql`.

## Production notes

- Keep `.env` out of VCS.
- In production, avoid localhost URLs and use real domain values.
- Backup and restore workflows are documented in:
  - `deploy/BACKUP.md`
  - `deploy/DEPLOY.md`
  - `deploy/templates/*`
