import * as Sentry from "@sentry/node";
import { nodeProfilingIntegration } from "@sentry/profiling-node";
import express from "express";
import dotenv from "dotenv";

import usersRouter from "./routes/users";
import ordersRouter from "./routes/orders";
import { syncRouter } from "./routes/sync";
import { configRouter } from "./routes/config";
import path from "path";

dotenv.config();

export const app = express();

// --- 1. Initialize Sentry AS EARLY AS POSSIBLE ---
Sentry.init({
  dsn: process.env.SENTRY_DSN || "",
  integrations: [
    nodeProfilingIntegration(),
  ],
  tracesSampleRate: 1.0,
  profilesSampleRate: 1.0,
});

// --- 2. Sentry Request Handler (must be first middleware) ---
Sentry.setupExpressErrorHandler(app);

app.use(express.json());

// --- 3. Mount Routes ---
app.use(express.static(path.join(__dirname, "public")));
app.use("/users", usersRouter);
app.use("/orders", ordersRouter);
app.use("/sync", syncRouter);
app.use("/config", configRouter);

app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

app.get("/debug-sentry", function mainHandler(req, res) {
  throw new Error("My first Sentry error!");
});

// --- 4. Sentry Error Handler (must be after all controllers, before fallback error handlers) ---
// Note: Sentry.setupExpressErrorHandler sets up BOTH the request handler and error handler automatically in v8+
// if you pass it the app instance at the top. But if manual is needed, we'd do it here. 
// With v8+, setupExpressErrorHandler handles it.

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`SlothOps Demo App running on port ${PORT}`);
});
