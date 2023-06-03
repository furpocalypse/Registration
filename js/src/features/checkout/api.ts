import {
  CheckoutResponse,
  PaymentServiceID,
} from "#src/features/checkout/types/Checkout.js"
import { Wretch } from "wretch"
import { queryStringAddon } from "wretch/addons"

/**
 * Create a checkout for a cart.
 * @param wretch - The {@link Wretch} instance.
 * @param cartId - The cart Id.
 * @param service - The service ID.
 * @param method - The checkout method.
 * @returns The created checkout info.
 */
export const createCheckout = async <ID extends PaymentServiceID>(
  wretch: Wretch,
  cartId: string,
  service: ID,
  method: string | undefined
): Promise<CheckoutResponse<ID>> => {
  const res = await wretch
    .url(`/carts/${cartId}/checkout`)
    .addon(queryStringAddon)
    .query({ service: service, method: method })
    .post()
    .json<CheckoutResponse<ID>>()

  return res
}

/**
 * Update a checkout.
 * @returns null if the checkout is complete, or additional checkout information if necessary.
 */
export const updateCheckout = async <ID extends PaymentServiceID>(
  wretch: Wretch,
  checkoutId: string,
  data?: Record<string, unknown>
): Promise<CheckoutResponse<ID> | null> => {
  let req = await wretch.url(`/checkouts/${checkoutId}/update`)

  if (data) {
    req = req.json(data)
  }

  const res = await req.post().res()

  if (res.status == 204) {
    return null
  } else {
    return await res.json()
  }
}

/**
 * Cancel a checkout by ID.
 */
export const cancelCheckout = async (
  wretch: Wretch,
  checkoutId: string
): Promise<void> => {
  await wretch.url(`/checkouts/${checkoutId}/cancel`).put().res()
}
