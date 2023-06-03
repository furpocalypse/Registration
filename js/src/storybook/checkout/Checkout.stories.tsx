import { CheckoutState } from "#src/features/checkout/CheckoutState.js"
import { CheckoutContainer } from "#src/features/checkout/components/checkout/CheckoutContainer.js"
import { CheckoutDialog } from "#src/features/checkout/components/checkout/CheckoutDialog.js"
import { CheckoutResponse } from "#src/features/checkout/types/Checkout.js"
import { getCheckoutComponent } from "#src/features/checkout/types/PaymentService.js"
import { Loader, createLoader } from "#src/util/loader.js"
import { useEffect, useState } from "react"

export default {
  title: "checkout/Checkout",
}

export const Mock = () => {
  const [id, setId] = useState(1)

  const [checkoutState, setCheckoutState] = useState<Loader<
    CheckoutState<"mock">
  > | null>(null)

  useEffect(() => {
    const factory = async () => {
      await new Promise((r) => window.setTimeout(r, 1000))

      const checkout: CheckoutResponse<"mock"> = {
        id: `${id}`,
        external_id: "checkout-1",
        service: "mock",
        data: {},
      }

      const updateMock = async (data?: Record<string, unknown>) => {
        await new Promise((r) => window.setTimeout(r, 1000))
        const card = data?.card
        const cardInt = typeof card == "string" ? parseInt(card) : undefined
        if (!cardInt || isNaN(cardInt) || cardInt == 0) {
          throw new Error("Invalid card")
        }
        return null
      }

      const cancelMock = async () => {
        await new Promise((r) => window.setTimeout(r, 1000))
      }

      return new CheckoutState(
        `cart-${id}`,
        "mock",
        undefined,
        checkout.id,
        checkout.id,
        checkout.data,
        () => getCheckoutComponent("mock"),
        updateMock,
        cancelMock
      )
    }

    const loader = createLoader(factory)
    setCheckoutState(loader)
  }, [id])

  return (
    <CheckoutDialog
      opened={!!checkoutState}
      onClose={() => {
        setId(id + 1)
      }}
    >
      {checkoutState && (
        <CheckoutContainer
          key={id}
          state={checkoutState}
          onClose={() => setId(id + 1)}
        />
      )}
    </CheckoutDialog>
  )
}
