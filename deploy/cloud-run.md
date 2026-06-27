# Cloud Run Deployment Notes

This prototype deploys as two services:

- `web/`: Next.js App Router app on Vercel.
- `server/`: FastAPI container on Cloud Run or another container runtime.

The browser never receives model or grounding secrets. Vercel only needs the
server-side `CRUCIBLE_API_BASE_URL` value for its route handler proxy.

## FastAPI On Cloud Run

Set these shell values first:

```bash
PROJECT_ID=your-gcp-project
REGION=europe-west3
REPOSITORY=hackthelaw
SERVICE=crucible-api
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$SERVICE:$(git rev-parse --short HEAD)"
```

Create the Artifact Registry repository once:

```bash
gcloud artifacts repositories create "$REPOSITORY" \
  --project "$PROJECT_ID" \
  --repository-format docker \
  --location "$REGION"
```

Build and push the FastAPI image:

```bash
gcloud builds submit server \
  --project "$PROJECT_ID" \
  --tag "$IMAGE"
```

That default image installs `server/requirements.txt`. For an ADK-enabled image,
build with the Docker build arg instead:

```bash
docker build \
  --build-arg REQUIREMENTS_FILE=requirements-adk.txt \
  -t "$IMAGE" \
  server
docker push "$IMAGE"
```

Deploy the service:

```bash
gcloud run deploy "$SERVICE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --image "$IMAGE" \
  --allow-unauthenticated \
  --port 8080
```

For the ADK-backed opponent runtime, use the ADK-enabled image above and set
backend-only environment variables on the Cloud Run service:

```text
CRUCIBLE_RUNNER=adk
CRUCIBLE_ADK_MODEL=your-gemini-model
GOOGLE_API_KEY=...
```

If the ADK, model, or Google credentials are missing, `/health` reports the
service as unconfigured and round endpoints return 503.

Verify the backend:

```bash
API_URL="$(gcloud run services describe "$SERVICE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --format 'value(status.url)')"
curl -fsS "$API_URL/health"
```

## Vercel Frontend

Set the Vercel project root to `web`.

Required Vercel environment variable:

```text
CRUCIBLE_API_BASE_URL=https://your-cloud-run-service-url
```

CLI path:

```bash
cd web
vercel link
vercel env add CRUCIBLE_API_BASE_URL production
vercel env add CRUCIBLE_API_BASE_URL preview
vercel deploy --prod
```

Verify the Vercel deployment after the FastAPI URL is configured:

```bash
WEB_URL=https://your-vercel-deployment-url
curl -fsS "$WEB_URL/api/health"
curl -fsS "$WEB_URL/api/crucible/health"
```

`/api/health` returns HTTP 503 when `CRUCIBLE_API_BASE_URL` is missing or the
backend cannot be reached. That is intentional: deployment should fail visibly
instead of silently running without the FastAPI service.

## Later Backend Secrets

Backend-only environment variables are listed in `server/.env.example`.
`PERPLEXITY_API_KEY`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, and
`GOOGLE_API_KEY` belong on the FastAPI service only. `CRUCIBLE_ADK_MODEL` is
not secret, but it still belongs on the FastAPI service because the browser
does not choose the model. Do not use `NEXT_PUBLIC_` for those values.
