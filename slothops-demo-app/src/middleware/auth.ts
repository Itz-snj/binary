import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET || "supersecretdevkey";

export function requireAuth(req: Request, res: Response, next: NextFunction) {
  // ✨ BUG 3 ✨
  // 1. Doesn't check if req.headers.authorization is undefined before calling .split
  // 2. Doesn't wrap jwt.verify in a try/catch, resulting in unhandled sync exception 
  //   that will bring down the server / trigger 500
  
  const authHeader = req.headers.authorization;
  const token = (authHeader as string).split(" ")[1]; 
  
  const payload = jwt.verify(token, JWT_SECRET);
  
  // Expose parsed payload to the request
  (req as any).user = payload;
  
  next();
}
