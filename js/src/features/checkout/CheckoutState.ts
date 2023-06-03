import { PaymentServiceMap } from "#src/features/checkout/types/Checkout.js"
import { CheckoutResponse } from "#src/features/checkout/types/Checkout.js"
import { PaymentServiceID } from "#src/features/checkout/types/Checkout.js"
import { CheckoutComponent } from "#src/features/checkout/types/CheckoutComponent.js"
import { Loader, createLoader } from "#src/util/loader.js"
import { action, makeAutoObservable } from "mobx"

/**
 * The state of an individual checkout as it is updated/completed.
 */
export class CheckoutState<ID extends PaymentServiceID> {
  /**
   * The cart ID.
   */
  cartId: string

  /**
   * The service ID
   */
  service: ID

  /**
   * The payment method.
   */
  method: string | null = null

  /**
   * The checkout ID on the server.
   */
  id: string

  /**
   * The checkout ID with the external service.
   */
  externalId: string

  /**
   * The data associated with the checkout.
   */
  data: PaymentServiceMap[ID]

  /**
   * Function to update the checkout.
   */
  updateFunc: (
    body?: Record<string, unknown>
  ) => Promise<CheckoutResponse<ID> | null>

  /**
   * Function to cancel the checkout.
   */
  cancelFunc: () => Promise<void>

  /**
   * Function to call when the checkout becomes complete.
   */
  onComplete: (() => void) | null

  /**
   * Loader for the checkout component.
   */
  component: Loader<CheckoutComponent<ID>>

  /**
   * Track loading operations.
   */
  private _loading = 1

  /**
   * The current error.
   */
  error: unknown = null

  /**
   * Whether the checkout is complete.
   */
  private _complete = false

  constructor(
    cartId: string,
    service: ID,
    method: string | undefined,
    id: string,
    externalId: string,
    data: PaymentServiceMap[ID],
    getComponent: () => Promise<CheckoutComponent<ID>>,
    updateFunc: (
      body?: Record<string, unknown>
    ) => Promise<CheckoutResponse<ID> | null>,
    cancelFunc: () => Promise<void>,
    onComplete?: () => void
  ) {
    this.cartId = cartId
    this.service = service
    this.method = method ?? null
    this.id = id
    this.externalId = externalId
    this.data = data
    this.component = createLoader(() => getComponent())
    this.updateFunc = updateFunc
    this.cancelFunc = cancelFunc
    this.onComplete = onComplete ?? null
    makeAutoObservable(this)
  }

  update(body?: Record<string, unknown>): Promise<CheckoutResponse<ID> | null> {
    return this.updateFunc(body)
  }

  cancel(): Promise<void> {
    return this.cancelFunc()
  }

  /**
   * Whether the checkout is in a loading state.
   */
  get loading(): boolean {
    return this._loading > 0
  }

  /**
   * Indicate that the checkout is in a loading state.
   */
  setLoading() {
    this._loading += 1
  }

  /**
   * Indicate that the checkout is done loading.
   */
  clearLoading() {
    this._loading -= 1
  }

  /**
   * Whether the checkout is complete.
   */
  get complete(): boolean {
    return this._complete
  }

  /**
   * Mark the checkout as complete.
   */
  setComplete() {
    this._complete = true
    this.onComplete && this.onComplete()
  }

  /**
   * Wrap a promise to update the loading state.
   */
  withLoading<T>(promise: Promise<T>): Promise<T> {
    this.setLoading()
    return promise.finally(() => {
      this.clearLoading()
    })
  }

  /**
   * Wrap a promise to update the error state.
   */
  withError<T>(promise: Promise<T>): Promise<T> {
    this.error = null
    return promise.catch(
      action((err) => {
        this.error = err
        throw err
      })
    )
  }

  /**
   * Wrap a promise to set the complete status.
   */
  withComplete<T>(promise: Promise<T>): Promise<T> {
    return promise.then(
      action((res) => {
        this.setComplete()
        return res
      })
    )
  }

  /**
   * Wrap a promise to manage the loading state and set the complete/error state.
   */
  wrapPromise<T>(promise: Promise<T>): Promise<T> {
    return this.withComplete(this.withError(this.withLoading(promise)))
  }
}
