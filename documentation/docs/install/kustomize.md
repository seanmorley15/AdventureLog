# Kubernetes with Kustomize

AdventureLog runs on Kubernetes with the [Kustomize](https://kustomize.io/) example in the repository. It has been tested on k8s; other Kustomize-capable distributions should work too.

## What's included

The example in [`k8s/base/`](https://github.com/seanmorley15/AdventureLog/tree/main/k8s/base) runs Standard Deployment:

| Resource | Purpose |
| -------- | ------- |
| `adventurelog-secret` (Secret) | The database password and Django `SECRET_KEY` |
| `adventurelog-db` (StatefulSet and Service) | PostGIS, with a 10 Gi volume |
| `adventurelog` (Deployment and Service) | The app on port 80, with a 10 Gi media volume |
| `adventurelog` (Ingress) | One public hostname |

## Install

1. Check the [requirements](getting_started.md#requirements). The app pod needs about 2 GB of memory on first start, and 1 GB afterward.
2. Copy `k8s/base/` and edit `adventurelog.yaml`:
   - Set the secret values. Keep `SECRET_KEY` once set: changing it signs everyone out.
   - Set `SITE_URL` to your public address.
   - Set the Ingress host to your domain.
3. Apply it:

   ```bash
   kubectl apply -k k8s/base/
   ```

4. Read the admin password from the app's log, as described in [First Steps](first_steps.md#_2-find-the-admin-password):

   ```bash
   kubectl logs deploy/adventurelog | grep -A3 "Admin username"
   ```

Every other setting is an environment variable on the `app` container. See [Environment Variables](../configuration/environment_variables.md).

The older [`k8s/legacy/`](https://github.com/seanmorley15/AdventureLog/blob/main/k8s/legacy/kustomization.yml) example, which puts the frontend, backend, and database in one pod, is deprecated.

## Separate frontend and backend

To run the frontend and backend as separate Deployments, use the Advanced Deployment images and settings (see [Advanced Deployment](docker.md#urls)), and route paths in the Ingress:

| Path | Service |
| ---- | ------- |
| `/media`, `/admin`, `/static`, `/accounts` | Backend |
| Everything else | Frontend |

The frontend's server also calls the backend directly: set `PUBLIC_SERVER_URL` to the backend's internal Service address.

## Tailscale

The [Tailscale Kubernetes operator](https://tailscale.com/kb/1185/kubernetes/) can expose AdventureLog on your tailnet without opening firewall ports. Its address resolves from outside the cluster but not from inside, so the pods can't reach it. [Expose the tailnet service to your cluster](https://tailscale.com/kb/1438/kubernetes-operator-cluster-egress#expose-a-tailnet-https-service-to-your-cluster-workloads) so they can.
