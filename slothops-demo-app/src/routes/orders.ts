import { Router } from "express";
import { getOrderById, getOrderSubtotal } from "../services/orderService";
import { requireAuth } from "../middleware/auth";

const router = Router();

// Uses our buggy auth middleware
router.get("/:id", requireAuth, (req, res) => {
  const order = getOrderById(req.params.id as string);
  if (!order) {
    return res.status(404).json({ error: "Order not found" });
  }
  res.json(order);
});

// Calculate subtotal
router.get("/:id/subtotal", (req, res) => {
  try {
    const subtotal = getOrderSubtotal(req.params.id);
    res.json({ orderId: req.params.id, subtotal });
  } catch (err: any) {
    if (err.message === "Order not found") {
      return res.status(404).json({ error: "Order not found" });
    }
    // Let other errors (like our TypeError bug) bubble up to Sentry
    throw err;
  }
});

export default router;
