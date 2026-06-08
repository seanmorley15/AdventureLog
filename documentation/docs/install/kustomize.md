# Kubernetes and Kustomize (k8s)

_AdventureLog can be run inside a kubernetes cluster using [kustomize](https://kustomize.io/)._

## Prerequisites

A working kubernetes cluster. AdventureLog has been tested on k8s, but any Kustomize-capable flavor should be easy to use.

Allocate at least **2 GB RAM** for first boot (world geography import) and **1 GB** steady-state for small clusters.

## Recommended layout

The maintained example lives in [`k8s/base/`](https://github.com/seanmorley15/AdventureLog/tree/main/k8s/base):

- **PostGIS** runs in its own StatefulSet (not co-located with the app)
- **AIO** runs as a single Deployment on port 80 — simpler ingress than the 3-container split
- **Secrets** for database and Django credentials (no hardcoded admin password)
- **Ingress** for a single public hostname

Apply it with:

```bash
kubectl apply -k k8s/base/
```

Edit `SITE_URL`, ingress host, and secret values before applying in production.

The legacy [`k8s/legacy/kustomization.yml`](https://github.com/seanmorley15/AdventureLog/blob/main/k8s/legacy/kustomization.yml) example is **deprecated** — it colocates frontend, backend, and database in one pod.

## Standard 3-container on Kubernetes

If you need separate frontend and backend Deployments, use the [standard Docker env reference](docker.md#configuration) and configure ingress path routing:

- Frontend: all paths **except** `/media`, `/admin`, `/static`, `/accounts`
- Backend: `/media`, `/admin`, `/static`, `/accounts`

The backend must be reachable **both** from browsers and from the frontend SSR process. Set `PUBLIC_SERVER_URL` to an internal service URL and configure public URLs separately — see the Docker docs.

## Tailscale and Headscale

Many k8s homelabs choose to use [Tailscale](https://tailscale.com/) or similar projects to remove the need for open ports in your home firewall.

The [Tailscale k8s Operator](https://tailscale.com/kb/1185/kubernetes/) will set up an externally resolvable service/ingress for your AdventureLog instance,
but it will fail to resolve internally.

You must [expose tailnet IPs to your cluster](https://tailscale.com/kb/1438/kubernetes-operator-cluster-egress#expose-a-tailnet-https-service-to-your-cluster-workloads) so the AdventureLog pods can resolve them.

## Environment Variables

Look at the [environment variable summary](docker.md#configuration) in the docker install section to see available and required configuration options. AIO installs can use `SITE_URL` and `POSTGRES_PASSWORD` with other values derived at startup.

Enjoy AdventureLog! 🎉
