# Testing and validation guidelines

## Minimum validation for backend/frontend changes

- Run frontend lint: `cd frontend && npm run lint`.
- Verify API health: `curl -I http://localhost/api/health/public`.
- Exercise affected user flow manually (login + impacted screen/action).

## Existing smoke script

- `frontend/tests/test_usuarios.sh` validates basic user route flow using cookies and curl.
- Script assumes local backend credentials and `jq` availability.

## Change-specific checks

- If auth or session logic changed, verify:
  - login
  - role-based route access
  - logout and localStorage cleanup
- If schema changed, verify affected CRUD endpoints and matching frontend service/view behavior.
- If upload/PDF changed, validate file upload, retrieval URL, and PDF generation endpoints.
