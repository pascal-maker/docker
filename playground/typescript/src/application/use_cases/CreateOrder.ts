import { Order } from "../../domain/entities/Order.js";
import type { Money } from "../../domain/value_objects/Money.js";
import type { OrderId } from "../../domain/value_objects/OrderId.js";

/** Create order use case. */
export function createOrder(orderId: OrderId, total: Money): Order {
  return new Order(orderId, total);
}
