import request from "supertest";
import { app } from "../src/index";

// Mock Sentry to avoid actual network calls during tests
jest.mock("@sentry/node", () => ({
  init: jest.fn(),
  setupExpressErrorHandler: jest.fn(),
  captureException: jest.fn(),
  flush: jest.fn().mockResolvedValue(true),
}));

describe("Express App", () => {
  describe("GET /health", () => {
    it("should return 200 with healthy status", async () => {
      const response = await request(app).get("/health");
      expect(response.status).toBe(200);
      expect(response.body).toEqual({ status: "healthy" });
    });
  });

  describe("GET /debug-sentry", () => {
    it("should return a 500 error and call Sentry", async () => {
      // Suppress console.error output from the error handler during this test
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
      
      const response = await request(app).get("/debug-sentry");
      
      expect(response.status).toBe(500);
      expect(response.body.message).toBe("Serverless Crash");
      expect(response.body.error).toBe("My first Sentry error!");

      // Verify Sentry functions were called
      const Sentry = require("@sentry/node");
      expect(Sentry.captureException).toHaveBeenCalled();
      expect(Sentry.flush).toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });
  });

  describe("GET /non-existent-route", () => {
    it("should return 404", async () => {
      const response = await request(app).get("/non-existent-route");
      expect(response.status).toBe(404);
    });
  });
});
