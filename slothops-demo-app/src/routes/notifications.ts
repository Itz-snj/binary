import { Router, Request, Response } from "express";

const router = Router();

// Dummy notification preferences endpoint
router.get("/preferences", (req: Request, res: Response) => {
  const userId = req.query.userId as string;
  if (!userId) {
    res.status(400).json({ error: "userId query param is required" });
    return;
  }
  
  // Simulated preferences
  res.json({
    userId,
    email: true,
    sms: false,
    push: true,
    frequency: "daily",
  });
});

// Dummy update notification preferences
router.post("/preferences", (req: Request, res: Response) => {
  const { userId, email, sms, push, frequency } = req.body;
  
  if (!userId) {
    res.status(400).json({ error: "userId is required in body" });
    return;
  }
  
  // In a real app, this would persist to a database
  console.log(`Updated notification prefs for user ${userId}`);
  
  res.json({
    message: "Notification preferences updated successfully",
    userId,
    email: email ?? true,
    sms: sms ?? false,
    push: push ?? true,
    frequency: frequency ?? "daily",
  });
});

export default router;
