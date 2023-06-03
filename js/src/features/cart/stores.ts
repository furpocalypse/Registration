import { fetchCart, fetchEmptyCart } from "#src/features/cart/api.js"
import { Cart } from "#src/features/cart/types.js"
import { getCurrentCartId, setCurrentCartId } from "#src/features/cart/utils.js"
import { Loader, createLoader } from "#src/util/loader.js"
import { makeAutoObservable, reaction, runInAction } from "mobx"
import { Wretch } from "wretch"

export class CartStore {
  loaders = new Map<string, Loader<Cart>>()

  constructor(public wretch: Wretch) {
    makeAutoObservable(this)
  }

  getCart(id: string): Cart | undefined {
    const loader = this.loaders.get(id)
    if (loader?.checkLoaded()) {
      return loader.value
    } else {
      return undefined
    }
  }

  load(id: string): Loader<Cart> {
    let loader = this.loaders.get(id)
    if (!loader) {
      loader = createLoader(() => fetchCart(this.wretch, id))
      this.loaders.set(id, loader)
    }

    return loader
  }
}

export class CurrentCartStore {
  currentCartId: string | null
  loader: Loader<Cart> | null = null

  constructor(
    public wretch: Wretch,
    public eventId: string,
    public cartStore: CartStore
  ) {
    this.currentCartId = getCurrentCartId() ?? null
    makeAutoObservable(this)

    reaction(
      () => this.currentCartId,
      (cartId) => {
        if (cartId) {
          setCurrentCartId(cartId)
        }
      }
    )
  }

  /**
   * Fetch the current cart by ID. Returns null if not found or if it does not match the
   * event.
   * @returns The current {@link Cart}, or null.
   */
  async checkCurrentCart(): Promise<Cart | null> {
    const id = this.currentCartId
    if (!id) {
      return null
    }

    const cart = await this.cartStore.load(id)

    if (!cart || cart.event_id != this.eventId) {
      return null
    }

    return cart
  }

  /**
   * Check that the current cart exists and matches the current event. If not, fetch the
   * empty cart and update the stored current cart ID.
   */
  async checkAndSetCurrentCart(): Promise<readonly [string, Cart]> {
    const curId = this.currentCartId
    const cur = await this.checkCurrentCart()
    if (cur) {
      runInAction(() => {
        this.loader = createLoader(async () => cur, cur)
      })
      return [curId as string, cur] as const
    }

    const [emptyId, empty] = await fetchEmptyCart(this.wretch, this.eventId)
    runInAction(() => {
      this.currentCartId = emptyId
      this.loader = createLoader(async () => empty, empty)
    })
    return [emptyId, empty] as const
  }

  /**
   * Clear the current cart.
   */
  clearCurrentCart() {
    this.currentCartId = null
    setCurrentCartId("")
    this.checkAndSetCurrentCart()
  }

  /**
   * Set the current cart ID.
   * @param id - The cart ID.
   * @param value - The cart, or loader for the cart.
   */
  setCurrentCart(id: string, value?: Cart | Loader<Cart>) {
    this.currentCartId = id

    if (value && "load" in value) {
      this.loader = value
    } else if (value) {
      this.loader = createLoader(async () => value, value)
    }
  }
}
