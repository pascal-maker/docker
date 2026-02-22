import type { Money } from "../value_objects/Money.js";

/** Domain entity: a product. */
export class Product {
  constructor(
    public readonly name: string,
    public readonly price: Money,
  ) {}
}
