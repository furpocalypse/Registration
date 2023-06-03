import { CheckoutState } from "#src/features/checkout/CheckoutState.js"
import {
  cancelCheckout,
  createCheckout,
  updateCheckout,
} from "#src/features/checkout/api.js"
import { PaymentServiceID } from "#src/features/checkout/types/Checkout.js"
import { getCheckoutComponent } from "#src/features/checkout/types/PaymentService.js"
import { Loader, createLoader } from "#src/util/loader.js"
import { action, makeAutoObservable } from "mobx"
import { Wretch } from "wretch"

/**
 * The page-level state of a checkout.
 *
 * This manages the state of the overall checkout process. Many checkouts may be created
 * and cancelled, until one becomes complete.
 */
export class CartCheckoutState {
  /**
   * The cart ID to checkout.
   */
  cartId: string

  /**
   * Track the overall complete status.
   */
  complete = false

  /**
   * Function to create a new checkout state.
   */
  createFunc: (
    cartId: string,
    service: PaymentServiceID,
    method?: string,
    onComplete?: (id: string) => void
  ) => Promise<CheckoutState<PaymentServiceID>>

  /**
   * The loader for the current checkout.
   */
  checkout: Loader<CheckoutState<PaymentServiceID>> | null = null

  /**
   * Called when the checkout is complete.
   */
  onComplete: ((id: string) => void) | null

  constructor(
    cartId: string,
    createFunc: (
      cartId: string,
      service: PaymentServiceID,
      method?: string
    ) => Promise<CheckoutState<PaymentServiceID>>,
    onComplete?: (id: string) => void
  ) {
    this.cartId = cartId
    this.createFunc = createFunc
    this.onComplete = onComplete ?? null
    makeAutoObservable(this)
  }

  static defaultStateFactory = (
    wretch: Wretch
  ): ((
    cartId: string,
    service: PaymentServiceID,
    method?: string
  ) => Promise<CheckoutState<PaymentServiceID>>) => {
    const factory = async (
      cartId: string,
      service: PaymentServiceID,
      method?: string,
      onComplete?: (id: string) => void
    ) => {
      const checkout = await createCheckout(wretch, cartId, service, method)
      const update = async (body?: Record<string, unknown>) => {
        const result = await updateCheckout(wretch, checkout.id, body)
        return result
      }
      const cancel = async () => {
        await cancelCheckout(wretch, checkout.id)
      }

      return new CheckoutState(
        cartId,
        service,
        method,
        checkout.id,
        checkout.external_id,
        checkout.data,
        () => getCheckoutComponent(service),
        update,
        cancel,
        onComplete ? () => onComplete(checkout.id) : undefined
      )
    }

    return factory
  }

  /**
   * Create a new checkout.
   */
  create(
    cartId: string,
    service: PaymentServiceID,
    method?: string
  ): Promise<CheckoutState<PaymentServiceID>> {
    const onComplete = action((id: string) => {
      this.complete = true
      this.onComplete && this.onComplete(id)
    })

    const loader = createLoader(() =>
      this.createFunc(cartId, service, method, onComplete)
    )
    this.checkout = loader
    return loader
  }
}
