import { CheckoutState } from "#src/features/checkout/CheckoutState.js"
import { PaymentServiceID } from "#src/features/checkout/types/Checkout.js"
import { ComponentType } from "react"

export interface CheckoutComponentProps<ID extends PaymentServiceID> {
  state: CheckoutState<ID>
}

export type CheckoutComponent<ID extends PaymentServiceID> = ComponentType<
  CheckoutComponentProps<ID>
>
