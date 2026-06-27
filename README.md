# Crucible Prototype C: Voice Sparring

This branch is a browser-native voice-first shell for the Crucible loop. It uses
browser speech recognition where available and browser speech synthesis for the
spoken reply, but opponent turns come from the configured FastAPI backend.

The frontend is a Next.js App Router app in `web/`, suitable for Vercel with
`web` as the project root. It does not expose API keys to the browser; all
round requests go through `/api/voice/*` to `CRUCIBLE_API_BASE_URL`.

## Run

```bash
cd web
npm install
CRUCIBLE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --port 3003
```

The FastAPI backend must be running with `CRUCIBLE_RUNNER=adk`, a model, and
Google credentials before a voice drill can start.

## Verify

```bash
cd web
npm test
npm run lint
npm run build
```
