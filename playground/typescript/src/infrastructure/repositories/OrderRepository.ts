import type { Order } from "../../domain/entities/Order.js";
import type { OrderId } from "../../domain/value_objects/OrderId.js";

/** In-memory order repository. */
export class OrderRepository {
  private readonly orders = new Map<string, Order>();

  save(order: Order): void {
    this.orders.set(order.orderId.value, order);
  }

  findById(orderId: OrderId): Order | null {
    return this.orders.get(orderId.value) ?? null;
  }
}
