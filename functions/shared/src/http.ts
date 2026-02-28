/** HTTP response type and handler wrapper for Cloud Functions. */

import type { Request, Response } from "express";

/** HTTP response for Cloud Functions. Use httpHandler to convert to Express response. */
export interface HttpResponse {
  body: string;
  status: number;
  headers?: Record<string, string>;
}

/** Handler that returns HttpResponse instead of writing to res directly. */
export type HttpHandlerFn = (
  req: Request,
  res: Response,
) => Promise<HttpResponse> | HttpResponse;

/** Wrapped handler type returned by httpHandler. Use for explicit annotations. */
export type HttpHandler = (req: Request, res: Response) => void | Promise<void>;

/**
 * Wraps a handler that returns HttpResponse and sends it via Express res.
 * Use this instead of writing to res directly for consistent response handling.
 */
export function httpHandler(
  handler: HttpHandlerFn,
): (req: Request, res: Response) => void | Promise<void> {
  return async (req: Request, res: Response): Promise<void> => {
    const response = await handler(req, res);
    if (response.headers) {
      for (const [key, value] of Object.entries(response.headers)) {
        res.setHeader(key, value);
      }
    }
    res.status(response.status).send(response.body);
  };
}
