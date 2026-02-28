/** Extend Express Request with rawBody for HMAC verification. */
import type { Request } from "express";

declare global {
  namespace Express {
    interface Request {
      /** Raw request body buffer (set by functions-framework for signature verification). */
      rawBody?: Buffer;
    }
  }
}
