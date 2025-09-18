# AdventureLog Development Instructions

AdventureLog is a self-hosted travel companion web application built with SvelteKit frontend and Django backend, deployed via Docker.

**ALWAYS follow these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Essential Setup (NEVER CANCEL - Set 60+ minute timeouts)
Run these commands in order:
- `cp .env.example .env` - Copy environment configuration
- `time docker compose up -d` - **FIRST TIME: 25+ minutes, NEVER CANCEL. Set timeout to 60+ minutes. Subsequent starts: <1 second**
- Wait 30+ seconds for services to fully initialize before testing functionality

### Development Workflow Commands
**Frontend (SvelteKit with Node.js):**
- `cd frontend && npm install` - **45+ seconds, NEVER CANCEL. Set timeout to 60+ minutes**
- `cd frontend && npm run build` - **32 seconds, set timeout to 60 seconds**
- `cd frontend && npm run dev` - Start development server (requires backend running)
- `cd frontend && npm run format` - **6 seconds** - Fix code formatting (ALWAYS run before committing)
- `cd frontend && npm run lint` - **6 seconds** - Check code formatting
- `cd frontend && npm run check` - **12 seconds** - Run Svelte type checking (3 errors, 19 warnings expected)

**Backend (Django with Python):**
- Backend development requires Docker - local Python pip install fails due to network timeouts
- `docker compose exec server python3 manage.py test` - **7 seconds** - Run tests (2/3 tests fail, this is expected)
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
- `cd frontend && npm run format` - **6 seconds** - Fix formatting issues
- `cd frontend && npm run lint` - **6 seconds** - Verify formatting is correct (should pass after format)
- `cd frontend && npm run check` - **12 seconds** - Type checking (some warnings expected)
- `cd frontend && npm run build` - **32 seconds** - Verify build succeeds

## Critical Development Notes

### Configuration Issues
- **KNOWN ISSUE**: Docker development setup has frontend-backend communication problems
- The frontend may display "500: Internal Error" when navigating beyond homepage
- For working application, use production Docker setup or modify `PUBLIC_SERVER_URL` in .env
- **DO NOT attempt to fix these configuration issues** - focus on code changes only

### Docker vs Local Development
- **PRIMARY METHOD**: Use Docker for all development (`docker compose up -d`)
- **AVOID**: Local Python development (pip install fails with network timeouts)
- **AVOID**: Trying to run backend outside Docker (requires complex GDAL/PostGIS setup)

### Expected Test Failures
- Frontend check: 3 errors and 19 warnings expected (accessibility and TypeScript issues)
- Backend tests: 2 out of 3 Django tests fail (API endpoint issues) - **DO NOT fix unrelated test failures**

### Build Timing (NEVER CANCEL)
- **Docker first startup**: 25+ minutes (image downloads)
- **Docker subsequent startups**: <1 second (images cached)
- **Frontend npm install**: 45 seconds
- **Frontend build**: 32 seconds
- **Tests and checks**: 6-12 seconds each

## Common Tasks

### Repository Structure
```
AdventureLog/
├── frontend/           # SvelteKit web application
│   ├── src/           # Source code
│   ├── package.json   # Node.js dependencies and scripts
│   └── static/        # Static assets
├── backend/           # Django API server
│   ├── server/        # Django project
│   ├── Dockerfile     # Backend container
│   └── requirements.txt # Python dependencies
├── docker-compose.yml # Main deployment configuration
├── .env.example       # Environment template
└── install_adventurelog.sh # Production installer
```

### Key Scripts and Files
- `frontend/package.json` - Contains all frontend build scripts
- `backend/server/manage.py` - Django management commands
- `docker-compose.yml` - Service definitions (frontend:8015, backend:8016, db:5432)
- `.env` - Environment configuration (copy from .env.example)

### Development vs Production
- **Development**: Use `docker compose up -d` with .env file
- **Production**: Use `./install_adventurelog.sh` installer script
- **CI/CD**: GitHub Actions in `.github/workflows/` handle testing and deployment

### Common Error Patterns
- **"500: Internal Error"**: Frontend-backend communication issue (expected in dev setup)
- **"Cannot connect to backend"**: Backend not started or wrong URL configuration
- **"pip install timeout"**: Network issue, use Docker instead of local Python
- **"Frontend build fails"**: Run `npm install` first, check Node.js version compatibility

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
```

## Important File Locations
- Configuration: `.env` file in repository root
- Frontend source: `frontend/src/`
- Backend source: `backend/server/`
- Static assets: `frontend/static/`
- Database: Handled by Docker PostgreSQL container
- Documentation: `documentation/` folder