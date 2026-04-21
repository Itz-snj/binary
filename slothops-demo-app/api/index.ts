import express, { Request, Response } from "express";
import * as Sentry from "@sentry/node";
import { nodeProfilingIntegration } from "@sentry/profiling-node";
import usersRouter from "../src/routes/users";
import ordersRouter from "../src/routes/orders";
import { syncRouter } from "../src/routes/sync";
import { configRouter } from "../src/routes/config";
import shippingRouter from "../src/routes/shipping";
import marketingRouter from "../src/routes/marketing";
import analyticsRouter from "../src/routes/analytics";

Sentry.init({
  dsn: process.env.SENTRY_DSN || "",
  integrations: [nodeProfilingIntegration()],
  tracesSampleRate: 1.0,
  profilesSampleRate: 1.0,
});

const app = express();
app.use(express.json());

app.use("/users", usersRouter);
app.use("/orders", ordersRouter);
app.use("/sync", syncRouter);
app.use("/config", configRouter);
app.use("/shipping", shippingRouter);
app.use("/marketing", marketingRouter);
app.use("/analytics", analyticsRouter);

app.get("/health", (req: Request, res: Response) => {
  res.json({ status: "ok" });
});

app.get("/", (req: Request, res: Response) => {
  res.json({ message: "SlothOps Demo API" });
});

module.exports = app;