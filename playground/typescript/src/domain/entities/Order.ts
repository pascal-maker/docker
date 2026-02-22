import type { Money } from "../value_objects/Money.js";
import type { OrderId } from "../value_objects/OrderId.js";

/** Domain entity: an order. */
export class Order {
  constructor(
    public readonly orderId: OrderId,
    public readonly total: Money,
  ) {}
}
