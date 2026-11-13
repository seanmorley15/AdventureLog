# Development Setup

Run AdventureLog from source in a **Dev Container**, to work on the code with hot reload, debugging, and all tools inside Docker. This guide uses **Windows with WSL 2**; on macOS or Linux, skip the WSL parts.

To run AdventureLog rather than develop it, use [Standard Deployment](standard.md).

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/), set to use the WSL 2 engine, and running.
- WSL 2 with a Linux distribution. Ubuntu is recommended. Install it from Windows PowerShell:

  ```bash
  wsl --install -d Ubuntu
  ```

- [Visual Studio Code](https://code.visualstudio.com/) with the **Dev Containers** and **WSL** extensions.

::: warning Before you start
- Use a real distribution such as Ubuntu, not the `docker-desktop` WSL distribution.
- Work in your Linux home folder (`/home/<user>`), not under `/mnt/c/`. File watching and container mounts misbehave on Windows drives.
- Turn on Docker for your distribution: **Docker Desktop → Settings → Resources → WSL Integration → Ubuntu**.
:::

## 1. Clone the repository

In a WSL terminal:

```bash
cd ~
git clone https://github.com/seanmorley15/AdventureLog.git
cd AdventureLog
```

To contribute, [fork the repository](https://github.com/seanmorley15/AdventureLog/fork) and clone your fork instead.

## 2. Create the env file

```bash
cp .env.advanced.example .env && sed -i 's/^DEBUG=.*/DEBUG=True/' .env
```

The other defaults work for development. The dev setup uses the same settings as [Advanced Deployment](docker.md); see [Environment Variables](../configuration/environment_variables.md) for the rest.

## 3. Open it in the Dev Container

1. Run `code .` in the project folder. VS Code shows that the folder is open **in WSL**.
2. Press **Ctrl + Shift + P** and choose **Dev Containers: Reopen in Container**.

VS Code builds the container, installs dependencies, and attaches to it. The first build takes about 30 seconds.

## 4. Start the app

In the VS Code terminal, inside the Dev Container:

```bash
docker compose -f docker/docker-compose.dev.yml up --build
```

It takes a minute or two. Then open:

| Service | Address |
| ------- | ------- |
| Frontend | [http://localhost:8015](http://localhost:8015) |
| Backend API | [http://localhost:8016](http://localhost:8016) |

The dev setup creates an admin account when `DJANGO_ADMIN_USERNAME`, `DJANGO_ADMIN_PASSWORD`, and `DJANGO_ADMIN_EMAIL` all have values. If you can't sign in, create one:

```bash
docker compose -f docker/docker-compose.dev.yml exec server python manage.py createsuperuser
```

The world data is imported only once, so later starts are faster.

To reset the database and media volumes:

```bash
docker compose -f docker/docker-compose.dev.yml down -v
```

## Troubleshooting

| Problem | Fix |
| ------- | --- |
| `The command 'docker' could not be found in this WSL 2 distro` | Start Docker Desktop, turn on WSL integration for Ubuntu, and restart Docker Desktop. |
| Slow builds or file changes not picked up | Move the project from `/mnt/c/...` to `/home/<user>/AdventureLog`. |

If you hit something not covered here, open a [GitHub issue](https://github.com/seanmorley15/AdventureLog/issues) so the docs can be improved. See also the [contributing guide](https://github.com/seanmorley15/AdventureLog/blob/main/CONTRIBUTING.md).
