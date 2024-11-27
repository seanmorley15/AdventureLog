# Installation with Nginx Proxy Manager

Nginx Proxy Manager is a simple and powerful tool that allows you to manage Nginx proxy hosts and SSL certificates. It is designed to be easy to use and configure, and it integrates well with Docker.

It is fairly simple to set up Nginx Proxy Manager with AdventureLog.

## Deploy AdventureLog using Docker

View the [Docker installation guide](docker.md) for instructions on how to deploy AdventureLog using Docker.

## Ensure Correct Environment Variables

- `ORIGIN` - The domain where you will be hosting AdventureLog. This is where the **frontend** will be served from.
- `PUBLIC_URL` - This needs to match the **outward port of the server** and be accessible from where the app is used. It is used for the creation of image URLs.

## Setup Docker Network

Ensure that the Nginx Proxy Manager and AdventureLog containers are on the same Docker network. You can create a new network using the following command:

```bash
docker network create nginx-proxy-manager
```

Add the folowing to the bottom of the `docker-compose.yml` file for the Nginx Proxy Manager service and the AdventureLog service.

```yaml
networks:
  default:
    external:
      name: nginx-proxy-manager
```

## Setting Up Nginx Proxy Manager

1. Install Nginx Proxy Manager on your server. You can find the installation instructions [here](https://nginxproxymanager.com/setup/).
2. Open the Nginx Proxy Manager web interface and log in with your credentials.
3. Add a new proxy host for the AdventureLog **frontend**:
   - **Domain Names**: Enter the domain name where you will be hosting AdventureLog.
   - **Scheme**: `http`
   - **Forward Hostname/IP**: `adventurelog-frontend` The name of the AdventureLog **frontend** container in the `docker-compose.yml` file.
   - **Forward Port**: `3000` This is the internal port of the AdventureLog **frontend** container so you will not need to change it even if you change the external port.
4. Add a new proxy host for the AdventureLog **backend**:
   - **Domain Names**: Enter the domain name where you will be hosting AdventureLog.
   - **Scheme**: `http`
   - **Forward Hostname/IP**: `adventurelog-backend` The name of the AdventureLog **backend** container in the `docker-compose.yml` file.
   - **Forward Port**: `80` This is the internal port of the AdventureLog **backend** container so you will not need to change it even if you change the external port.

This will allow you to access AdventureLog using the domain name you specified in the Nginx Proxy Manager configuration.
