import {
  PaymentServiceID,
  PaymentServiceMap,
} from "#src/features/checkout/types/Checkout.js"
import { CheckoutComponent } from "#src/features/checkout/types/CheckoutComponent.js"

// export const checkoutComponents: Record<
//   PaymentServiceID,
//   () => Promise<CheckoutComponent<PaymentServiceID>>
// > = {
export const checkoutComponents: {
  [K in keyof PaymentServiceMap]?: () => Promise<CheckoutComponent<K>>
} = {
  mock: async () => {
    const module = await import(
      "#src/features/checkout/impl/mock/MockCheckoutComponent.js"
    )
    return module.MockCheckoutComponent
  },
  stripe: async () => {
    const module = await import(
      "#src/features/checkout/impl/stripe/StripeCheckoutComponent.js"
    )
    return await module.StripeCheckoutComponent
  },
}

export const getCheckoutComponent = async <ID extends PaymentServiceID>(
  service: ID
): Promise<CheckoutComponent<ID>> => {
  const promise = checkoutComponents[service]
  if (!promise) {
    throw new Error("Payment service unavailable")
  }
  const component = await promise()
  return component
}
