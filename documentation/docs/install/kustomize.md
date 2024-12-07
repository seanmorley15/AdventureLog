# Kustomize (k8s)

_AdventureLog can be run inside a kubernetes cluster using [kustomize](https://kustomize.io/)._

## Prerequisites

A working kubernetes cluster. AdventureLog has been tested on k8s, but any Kustomize-capable flavor should be easy to use.

## Cluster Routing
Because the AdventureLog backend must be reachable by **both** the web browser and the AdventureLog frontend, k8s-internal routing mechanisms traditional for standing up other similar applications **cannot** be used.

In order to host AdventureLog in your cluster, you must therefor configure an internally and externally resolvable ingress that routes to your AdventureLog backend container.

Once you have made said ingress, set `PUBLIC_SERVER_URL` and `PUBLIC_URL` env variables below to the url of that ingress.

## Tailscale and Headscale
Many k8s homelabs choose to use [Tailscale](https://tailscale.com/) or similar projects to remove the need for open ports in your home firewall.

The [Tailscale k8s Operator](https://tailscale.com/kb/1185/kubernetes/) will set up an externally resolvable service/ingress for your AdventureLog instance
but it will fail to resolve internally.

You must [expose tailnet IPs to your cluster](https://tailscale.com/kb/1438/kubernetes-operator-cluster-egress#expose-a-tailnet-https-service-to-your-cluster-workloads) so the AdventureLog pods can resolve them.

## Getting Started

Take a look at the [example config](kustomize_example.md) and modify it for your usecase.

## Environment Variables

Look at the [environment variable summary](docker.md#configuration) in the docker install section to see available and required configuration options.

### Frontend Container (web)

| Name                | Required  | Description                                                                                                                                                   | Default Value         |
| ------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `PUBLIC_SERVER_URL` | Yes       | What the frontend SSR server uses to connect to the backend.                                                                                                  | http://server:8000    |
| `ORIGIN`            | Sometimes | Not needed if using HTTPS. If not, set it to the domain of what you will acess the app from.                                                                  | http://localhost:8015 |
| `BODY_SIZE_LIMIT`   | Yes       | Used to set the maximum upload size to the server. Should be changed to prevent someone from uploading too much! Custom values must be set in **kiliobytes**. | Infinity              |

### Backend Container (server)

| Name                    | Required | Description                                                                                                                                   | Default Value           |
| ----------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| `PGHOST`                | Yes      | Databse host.                                                                                                                                 | db                      |
| `PGDATABASE`            | Yes      | Database.                                                                                                                                     | database                |
| `PGUSER`                | Yes      | Database user.                                                                                                                                | adventure               |
| `PGPASSWORD`            | Yes      | Database password.                                                                                                                            | changeme123             |
| `DJANGO_ADMIN_USERNAME` | Yes      | Default username.                                                                                                                             | admin                   |
| `DJANGO_ADMIN_PASSWORD` | Yes      | Default password, change after inital login.                                                                                                  | admin                   |
| `DJANGO_ADMIN_EMAIL`    | Yes      | Default user's email.                                                                                                                         | admin@example.com       |
| `PUBLIC_URL`            | Yes      | This needs to match the outward port of the server and be accessible from where the app is used. It is used for the creation of image urls.   | 'http://localhost:8016' |
| `CSRF_TRUSTED_ORIGINS`  | Yes      | Need to be changed to the orgins where you use your backend server and frontend. These values are comma seperated.                            | http://localhost:8016   |
| `FRONTEND_URL`          | Yes      | This is the publically accessible url to the **frontend** container. This link should be accessable for all users. Used for email generation. | 'http://localhost:8015' |


Enjoy AdventureLog! 🎉
