# SlothOps Dashboard (React)

Replaces `static/index.html` as the main operator UI. Scaffolded as
part of the Phase 1 restructure — the API surface it talks to lands
in Phase 2.

## Layout

```
web/
  index.html            Vite entry
  vite.config.ts        Dev proxy points at FastAPI on :8000
  src/
    main.tsx            React + Router + QueryClient bootstrap
    app/
      App.tsx           Routes
      AppShell.tsx      Sidebar + outlet
    pages/              One file per route
    lib/api.ts          Fetch wrapper with JWT
    api/                Per-resource client (auth.ts, dashboard.ts, ...)
```

## Develop

```sh
cd web
npm install
npm run dev          # http://localhost:5173, proxies /api → :8000
```

## Build

```sh
npm run build        # outputs to web/dist
```

FastAPI does not serve this yet. Once the API surface is stable,
mount `web/dist` as a static directory or hand it to a CDN.
