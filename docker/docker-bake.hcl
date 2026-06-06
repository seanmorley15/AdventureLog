# Build all AdventureLog app images from the unified Dockerfile.
# Usage (from repository root):
#   docker buildx bake -f docker/docker-bake.hcl
#   docker buildx bake -f docker/docker-bake.hcl frontend

group "default" {
  targets = ["frontend", "backend", "aio"]
}

target "_common" {
  context    = ".."
  dockerfile = "docker/Dockerfile"
}

target "frontend" {
  inherits = ["_common"]
  target   = "frontend"
  tags     = ["adventurelog-frontend:local"]
}

target "backend" {
  inherits = ["_common"]
  target   = "backend"
  tags     = ["adventurelog-backend:local"]
}

target "aio" {
  inherits = ["_common"]
  target   = "aio"
  tags     = ["adventurelog-aio:local"]
}
