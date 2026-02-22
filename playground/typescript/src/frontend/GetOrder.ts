import type { Order } from "../domain/entities/Order.js";

/**
 * VIOLATION: Backend use case placed in frontend.
 * Should live in application/use_cases/. Refactoring to enforce
 * frontend/backend boundary would move it and update imports.
 */
export function getOrderHandler(orderId: string): Order | null {
  return null;
}
