# Crucible Prototype C: Voice Sparring

This branch is a browser-native voice-first prototype of the Crucible loop. It
uses browser speech recognition where available, browser speech synthesis for
the sparring partner, and keeps text controls as the reliable path for demos.

The frontend is a Next.js App Router app in `web/`, suitable for Vercel with
`web` as the project root. It does not expose API keys to the browser.

## Run

```bash
cd web
npm install
npm run dev
```

## Verify

```bash
cd web
npm test
npm run lint
npm run build
```
