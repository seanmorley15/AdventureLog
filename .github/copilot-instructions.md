# AdventureLog Development Instructions

AdventureLog is a self-hosted travel companion web application built with SvelteKit frontend and Django backend, deployed via Docker.

**ALWAYS follow these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Essential Setup (NEVER CANCEL - Set 60+ minute timeouts)
Run these commands in order:
- `cp .env.example .env` - Copy Standard Deployment environment configuration
- `cp .env.advanced.example .env.advanced` - Copy Advanced Deployment environment configuration
- `time docker compose up -d` - **FIRST TIME: 25+ minutes, NEVER CANCEL. Set timeout to 60+ minutes. Subsequent starts: <1 second**
- Wait 30+ seconds for services to fully initialize before testing functionality

### Development Workflow Commands
**Frontend (SvelteKit with Node.js / pnpm):**
- `cd frontend && pnpm install` - Install dependencies (NEVER CANCEL on first install)
- `cd frontend && pnpm run build` - Production build
- `cd frontend && pnpm run dev` - Start development server (requires backend running)
- `cd frontend && pnpm run format` - Fix code formatting (ALWAYS run before committing)
- `cd frontend && pnpm run lint` - Check code formatting
- `cd frontend && pnpm run check` - Run Svelte type checking

**Backend (Django with Python):**
- Preferred: `./scripts/test-backend.sh` — starts PostGIS if needed and runs the full Django suite with coverage (same as CI)
- Or with Docker: start DB via `docker compose -f docker/docker-compose.database.yml up -d`, then from `backend/server` with `DJANGO_SETTINGS_MODULE=main.settings_test` run `python manage.py test`
- `docker compose exec server python3 manage.py help` - View Django commands
- `docker compose exec server python3 manage.py migrate` - Run database migrations

**Full Application:**
- Frontend runs on: http://localhost:8015
- Backend API runs on: http://localhost:8016
- Default admin credentials: admin/admin (from .env file)

## Validation

### MANDATORY End-to-End Testing
**ALWAYS manually validate any new code by running through complete user scenarios:**
1. **ALWAYS run the bootstrapping steps first** (copy .env, docker compose up)
2. **Navigate to http://localhost:8015** - Verify homepage loads correctly
3. **Test basic functionality** - Homepage should display travel companion interface
4. **CRITICAL**: Some login/navigation may fail due to frontend-backend communication issues in development Docker setup. This is expected.

### Pre-Commit Validation (ALWAYS run before committing)
**ALWAYS run these commands to ensure CI will pass:**
- `./scripts/test-backend.sh` when backend code changed — the suite must pass (failures are not expected)
- `cd frontend && pnpm run format` - Fix formatting issues
- `cd frontend && pnpm run lint` - Verify formatting is correct (should pass after format)
- `cd frontend && pnpm run check` - Type checking
- `cd frontend && pnpm run build` - Verify build succeeds

## Critical Development Notes

### Configuration Issues
- **KNOWN ISSUE**: Docker development setup has frontend-backend communication problems
- The frontend may display "500: Internal Error" when navigating beyond homepage
- For working application, use production Docker setup or modify `PUBLIC_SERVER_URL` in .env
- **DO NOT attempt to fix these configuration issues** - focus on code changes only

### Docker vs Local Development
- **PRIMARY METHOD**: Use Docker for running the full app (`docker compose up -d`)
- **Backend tests**: Prefer `./scripts/test-backend.sh` (PostGIS via compose + local Python with GDAL)
- Local Python for the full server still needs GDAL/PostGIS; use Docker for day-to-day API work if setup is painful

### Test Expectations
- Backend Django tests must pass in CI and via `./scripts/test-backend.sh`
- Frontend `pnpm run lint` / `check` / `build` must pass for frontend changes
- Do not treat failing backend tests as "expected"

### Build Timing (NEVER CANCEL)
- **Docker first startup**: 25+ minutes (image downloads)
- **Docker subsequent startups**: <1 second (images cached)
- **Frontend pnpm install**: 45 seconds
- **Frontend build**: 32 seconds
- **Backend test suite**: typically under a few minutes with PostGIS ready

## Common Tasks

### Repository Structure
```
AdventureLog/
├── frontend/           # SvelteKit web application
│   ├── src/           # Source code
│   ├── package.json   # Node.js dependencies and scripts
│   └── static/        # Static assets
├── backend/           # Django API server
│   └── server/        # Django project + requirements
├── docker/            # Dockerfile, compose stacks, and shared configs
│   ├── docker-compose.advanced.yml
│   ├── docker-compose.database.yml
│   └── docker-compose.dev.yml
├── docker-compose.yml        # Standard Deployment (single container)
├── scripts/           # Install, deploy, test-backend.sh
├── k8s/               # Kubernetes / Kustomize manifests
├── .env.example              # Standard Deployment env template
├── .env.advanced.example     # Advanced Deployment env template
└── install_adventurelog.sh # Production installer
```

### Key Scripts and Files
- `frontend/package.json` - Contains all frontend build scripts
- `backend/server/manage.py` - Django management commands
- `scripts/test-backend.sh` - Run Django tests (CI parity)
- `docker-compose.yml` - Standard Deployment (single port:8015)
- `docker/docker-compose.advanced.yml` - Advanced Deployment service definitions (frontend:8015, backend:8016, db:5432)
- `.env` - Standard Deployment configuration (copy from .env.example)
- `.env.advanced` - Advanced Deployment configuration (copy from .env.advanced.example)

### Development vs Production
- **Development**: Use `docker compose -f docker/docker-compose.dev.yml up --build` or Standard Deployment compose with .env
- **Production**: Use `./install_adventurelog.sh` installer script
- **CI/CD**: GitHub Actions in `.github/workflows/` run backend tests, frontend quality, compose smoke, docs build, Trivy, and image publishes

### Common Error Patterns
- **"500: Internal Error"**: Frontend-backend communication issue (expected in dev setup)
- **"Cannot connect to backend"**: Backend not started or wrong URL configuration
- **"pip install timeout"**: Network issue; retry or use Docker for the app, tests still via `./scripts/test-backend.sh`
- **"Frontend build fails"**: Run `pnpm install` first, check Node.js version compatibility

## Troubleshooting Commands
```bash
# Check Docker services status
docker compose ps

# View service logs
docker compose logs web      # Frontend logs
docker compose logs server   # Backend logs
docker compose logs db       # Database logs

# Restart specific service
docker compose restart web   # Frontend only
docker compose restart server # Backend only

# Complete restart
docker compose down && docker compose up -d

# Backend tests only (PostGIS)
./scripts/test-backend.sh
```

## Important File Locations
- Configuration: `.env` file in repository root
- Frontend source: `frontend/src/`
- Backend source: `backend/server/`
- Static assets: `frontend/static/`
- Database: Handled by Docker PostgreSQL/PostGIS container
- Documentation: `documentation/` folder
