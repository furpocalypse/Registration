import { CheckoutComponentStateContext } from "#src/features/checkout/types/CheckoutComponentState.js"
import { CheckoutStateContext } from "#src/features/checkout/types/CheckoutState.js"
import { useContext } from "react"

export const useCheckoutState = () => useContext(CheckoutStateContext)

export const useCheckoutComponentState = () =>
  useContext(CheckoutComponentStateContext)
