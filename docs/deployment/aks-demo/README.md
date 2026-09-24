# AKS Deployment Demo (2026-09-23)

One-time deployment of CourseFlow to Azure Kubernetes Service, run to demonstrate
Docker + AKS skills. The cluster was torn down immediately after capturing this
evidence to avoid ongoing billing — these files are the permanent record.

## What was deployed

- **Cluster**: AKS, 1 node, `Standard_D2as_v7` (2 vCPU / 8GiB), ACR-attached
- **Registry**: Azure Container Registry (`courseflowacr`), images built via
  `az acr build` (cloud-side build, no local push)
- **Namespace**: `courseflow`
- **Backend**: FastAPI, 1 replica, `ClusterIP` Service (internal only), data
  (SQLite + ChromaDB) baked into the image
- **Frontend**: nginx serving the Vite/React build, 1 replica, `LoadBalancer`
  Service (public IP), reverse-proxying `/api/` to the backend Service via
  in-cluster DNS

## Evidence

- [`kubectl-get-pods.txt`](kubectl-get-pods.txt) — both pods `Running`
- [`kubectl-get-svc.txt`](kubectl-get-svc.txt) — frontend `LoadBalancer` with a
  real public `EXTERNAL-IP`
- [`browser-query-success.png`](browser-query-success.png) — a real end-to-end
  query against the public IP, streamed answer + cited source
- [`azure-portal-aks-cluster.png`](azure-portal-aks-cluster.png) — the AKS
  cluster's Overview page in the Azure Portal (Running, Kubernetes 1.35.8,
  attached to `courseflowacr`)
- `namespace.yaml`, `configmap.yaml`, `backend.yaml`, `frontend.yaml` — the
  exact manifests applied to the cluster

## Notable bug found and fixed during this deployment

`src/frontend/src/api/client.js` used `import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'`.
The build intentionally sets `VITE_API_BASE_URL=""` (empty string) so the
frontend makes same-origin relative requests through the nginx proxy. But `||`
treats `""` as falsy, so every deployed instance silently fell back to
`http://localhost:8000` — the *visitor's own* machine, not the cluster. Fixed
by switching to `??` (nullish coalescing), which only falls back on
`null`/`undefined`. Rebuilt and redeployed as `courseflow-frontend:v2`.
