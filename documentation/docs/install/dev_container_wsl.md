# Dev Container + WSL 🧰

Running AdventureLog in a **Dev Container** allows you to contribute to the project or work on features locally in a fully reproducible development environment with hot reloading, debugging, and tooling isolated inside Docker.

This guide focuses on **Windows using WSL 2**, but the workflow is similar on other platforms.

## Prerequisites

Before starting, ensure you have the following installed:

* **Docker Desktop**
  Download from: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)

  > Docker Desktop must be configured to use **WSL 2**
  > Make sure Docker Desktop is running before you start the steps below.

* **WSL 2 with a Linux distribution installed**
  Ubuntu is recommended.

  ```bash
  wsl --install -d Ubuntu
  ```
  Run this in **Windows PowerShell** (or **Windows Terminal**).

* **Visual Studio Code**
  [https://code.visualstudio.com/](https://code.visualstudio.com/)

* **VS Code Extensions**

  * Dev Containers
  * WSL

## ⚠️ Important Notes (Read First)

> **TIP**
> Do not use the `docker-desktop` WSL distribution for development.
> Always use a real Linux distro such as **Ubuntu**.

> **TIP**
> Avoid working in `/mnt/c/...`.
> Clone and work inside your Linux home directory (`/home/<user>`), otherwise file watching and container mounts may behave incorrectly.

> **TIP**
> Docker must be available *inside* WSL. Make sure WSL integration is enabled in Docker Desktop:
>
> **Docker Desktop → Settings → Resources → WSL Integration → Enable Ubuntu**

## Getting Started

### 1. Clone the Repository (inside WSL)

Open a WSL terminal (search for "WSL" in the Windows Start menu and open the WSL terminal), then run:

```bash
cd ~
git clone https://github.com/seanmorley15/AdventureLog.git
cd AdventureLog
```

> **TIP**
> If you plan to contribute changes, fork the repository on GitHub and clone your fork instead:
>
> ```bash
> git clone https://github.com/<your-username>/AdventureLog.git
> ```

### 2. Create the Development `.env` File (via WSL)

```bash
cp .env.example .env && sed -i 's/^DEBUG=.*/DEBUG=True/' .env
```

This creates the `.env` file required for the containers to start and enables DEBUG for local development.

> **NOTE**
> The rest of the defaults in `.env.example` are sufficient for running the project.

#### Environment Variables

The Dev Container setup uses the same `.env` configuration as the standard Docker installation.

For a full list of available environment variables and optional configuration options, see the
[**Docker 🐋 installation guide**](docker.md#configuration).

### 3. Open the Project in VS Code (via WSL)

From the project directory:

```bash
code .
```

VS Code should indicate that the folder is opened **in WSL**.

### 4. Reopen the Project in a Dev Container

In VS Code:

1. Press **Ctrl + Shift + P**
2. Select **Dev Containers: Reopen in Container**

VS Code will:

* Build the development containers
* Install dependencies
* Attach the editor to the running container

The first build usually takes around 30 seconds.

## Running the Application

Once the Dev Container is running, the services are started using Docker Compose.
Use the VS Code terminal (inside the Dev Container) for the commands below.

To start the app, enter the following command:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Bringing the app up usually takes around 1-2 minutes.

To fully reset the database and media volumes, run:

```bash
docker compose -f docker-compose.dev.yml down -v
```

## Accessing the App

* **Frontend (Web UI)**
  [http://localhost:8015](http://localhost:8015)

* **Backend (API)**
  [http://localhost:8016](http://localhost:8016)

Admin credentials are taken from your `.env` file. The `docker-compose.dev.yml` setup auto-creates a superuser on startup using those values so you can log in right away.
It also checks whether the countries/flags data already exists before re-importing it, so the first build can take longer and subsequent `down`/`up` runs are faster.
This dev setup can feel a bit slower because hot reload, dependency installs, and initial database bootstrapping all happen inside containers.

## Common Issues

### Docker Not Found Inside WSL

If you see:

```
The command 'docker' could not be found in this WSL 2 distro
```

Ensure:

* Docker Desktop is running
* WSL integration is enabled for **Ubuntu**
* Docker Desktop has been restarted after enabling integration

### Accidentally Using `/mnt/c`

If the project lives under `/mnt/c/...`, move it to:

```bash
/home/<user>/AdventureLog
```

This avoids performance issues and file watcher bugs.

## Dev vs Production

| Feature      | Docker Install  | Dev Container      |
| ------------ | --------------- | ------------------ |
| Intended use | Running the app | Developing the app |
| Hot reload   | ❌               | ✅                  |
| Debugging    | ❌               | ✅                  |
| Code editing | ❌               | ✅                  |

For production or personal hosting, follow the standard
[**Docker 🐋 installation guide**](docker.md).

Enjoy contributing to AdventureLog! 🎉
If you run into issues not covered here, please open a discussion or issue so the docs can be improved.
