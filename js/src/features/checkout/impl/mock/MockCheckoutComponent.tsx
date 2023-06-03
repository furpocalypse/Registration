import { CheckoutState } from "#src/features/checkout/CheckoutState.js"
import { Button, Stack, TextInput } from "@mantine/core"
import { useEffect, useState } from "react"

export type MockCheckoutData = Record<string, unknown>

declare module "#src/features/checkout/types/Checkout.js" {
  interface PaymentServiceMap {
    mock: MockCheckoutData
  }
}

export type MockCheckoutComponentProps = {
  state: CheckoutState<"mock">
}

export const MockCheckoutComponent = ({
  state,
}: MockCheckoutComponentProps) => {
  const [cardValue, setCardValue] = useState("")

  const paymentHandler = async (cardValue: string) => {
    await new Promise((r) => window.setTimeout(r, 1000))
    await state.updateFunc({ card: cardValue })
  }
  const setup = () => new Promise((r) => window.setTimeout(r, 1000))

  useEffect(() => {
    state.withLoading(setup()).then(() => {
      state.clearLoading()
    })
  }, [])

  return (
    <form>
      <Stack>
        <TextInput
          placeholder="Card #"
          inputMode="numeric"
          value={cardValue}
          onChange={(e) => {
            setCardValue(e.target.value)
          }}
        />
        <Button
          onClick={() => {
            if (state.loading) {
              return
            }
            state.wrapPromise(paymentHandler(cardValue))
          }}
        >
          Checkout
        </Button>
      </Stack>
    </form>
  )
}
