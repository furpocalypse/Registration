import { Wretch } from "wretch"
import { queryStringAddon } from "wretch/addons"
import { Cart, PricingResult } from "#src/features/cart/types.js"
import { InterviewStateResponse } from "@oes/interview-lib"
import { CheckoutMethod } from "#src/features/checkout/types/Checkout.js"

/**
 * Fetch the empty cart for an event.
 */
export const fetchEmptyCart = async (
  wretch: Wretch,
  eventId: string
): Promise<[string, Cart]> => {
  const res = await wretch
    .url("/carts/empty")
    .addon(queryStringAddon)
    .query({ event_id: eventId })
    .get()
    .res()

  const body: Cart = await res.json()

  const url = new URL(res.url)
  const pathParts = url.pathname.split("/")
  const id = pathParts[pathParts.length - 1]

  return [id, body]
}

/**
 * Fetch a cart by ID.
 */
export const fetchCart = async (
  wretch: Wretch,
  cartId: string
): Promise<Cart> => {
  const res = await wretch.url(`/carts/${cartId}`).get().json<Cart>()

  return res
}

/**
 * Fetch the pricing result for a cart.
 */
export const fetchCartPricingResult = async (
  wretch: Wretch,
  cartId: string
) => {
  const res = await wretch
    .url(`/carts/${cartId}/pricing-result`)
    .get()
    .json<PricingResult>()
  return res
}

/**
 * Fetch a new interview state for a cart.
 */
export const fetchCartInterview = async (
  wretch: Wretch,
  cartId: string,
  interviewId: string,
  registrationId?: string
): Promise<InterviewStateResponse> => {
  const res = await wretch
    .url(`/carts/${cartId}/new-interview`)
    .addon(queryStringAddon)
    .query({
      interview_id: interviewId,
      registration_id: registrationId,
    })
    .get()
    .json<InterviewStateResponse>()

  return res
}

/**
 * Fetch the available checkout methods for a cart.
 */
export const fetchAvailableCheckoutMethods = async (
  wretch: Wretch,
  cartId: string
): Promise<CheckoutMethod[]> => {
  const res = await wretch
    .url(`/carts/${cartId}/checkout-methods`)
    .get()
    .json<CheckoutMethod[]>()
  return res
}
