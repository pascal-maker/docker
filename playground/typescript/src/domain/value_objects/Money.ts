/** Money value object. */
export class Money {
  constructor(
    public readonly amount: number,
    public readonly currency: string = "USD",
  ) {}
}
