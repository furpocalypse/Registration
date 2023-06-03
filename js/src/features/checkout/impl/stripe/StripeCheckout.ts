import { CheckoutState } from "#src/features/checkout/CheckoutState.js"
import { Stripe, StripeElements, StripePaymentElement } from "@stripe/stripe-js"

declare module "#src/features/checkout/types/Checkout.js" {
  interface PaymentServiceMap {
    stripe: StripeCheckoutData
  }
}

export interface StripeCheckoutData {
  publishable_key: string
  amount: number
  currency: string
  next_action?: boolean
  client_secret?: string
}

export class StripeCheckout {
  elements: StripeElements
  paymentElement: StripePaymentElement

  constructor(
    public checkoutState: CheckoutState<"stripe">,
    public stripe: Stripe
  ) {
    this.elements = stripe.elements({
      mode: "payment",
      amount: this.checkoutState.data.amount,
      currency: this.checkoutState.data.currency,
      paymentMethodCreation: "manual",
    })
    this.paymentElement = this.elements.create("payment", {})
  }

  async createPaymentMethod(): Promise<string> {
    const res = await this.elements.submit()
    if (res.error) {
      throw new Error(res.error.message)
    }

    const createRes = await this.stripe.createPaymentMethod({
      element: this.paymentElement,
    })
    if (createRes.error) {
      throw new Error(createRes.error.message)
    }

    return createRes.paymentMethod.id
  }

  async handleNextAction(clientSecret: string): Promise<string> {
    const res = await this.stripe.handleNextAction({
      clientSecret: clientSecret,
    })

    if (res.error) {
      throw new Error(res.error.message)
    }

    return res.paymentIntent?.payment_method as string
  }

  async handleSubmit() {
    const paymentMethodId = await this.createPaymentMethod()
    const payResult = await this.checkoutState.update({
      payment_method: paymentMethodId,
    })

    if (
      payResult &&
      payResult.data.next_action &&
      payResult.data.client_secret
    ) {
      const nextId = await this.handleNextAction(
        payResult.data.client_secret as string
      )
      const nextPayResult = await this.checkoutState.update({
        payment_method: nextId,
      })
      if (nextPayResult != null) {
        throw new Error("Payment confirmation failed")
      }
    }
  }
}
