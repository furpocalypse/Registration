import { CheckoutState } from "#src/features/checkout/CheckoutState.js"
import { StripeCheckout } from "#src/features/checkout/impl/stripe/StripeCheckout.js"
import { Box, Button, Stack } from "@mantine/core"
import { loadStripe } from "@stripe/stripe-js"
import { useEffect, useState } from "react"

export const StripeCheckoutComponent = ({
  state,
}: {
  state: CheckoutState<"stripe">
}) => {
  const [stripe, setStripe] = useState<StripeCheckout | null>(null)
  const [mounted, setMounted] = useState(false)

  // very messy
  const [refFunc, setRefFunc] = useState<
    ((cur: HTMLDivElement | null) => void) | null
  >(null)

  // setup on mount
  useEffect(() => {
    const setup = async () => {
      const stripe = await loadStripe(state.data.publishable_key)
      if (!stripe) {
        throw new Error("Could not load Stripe")
      }

      const checkout = new StripeCheckout(state, stripe)

      const refFunc = (cur: HTMLDivElement | null) => {
        if (cur) {
          setMounted(true)
          checkout.paymentElement.mount(cur)
        } else {
          try {
            checkout.paymentElement.unmount()
          } catch (_) {
            // ignore
          }
        }
      }

      setStripe(checkout)
      setRefFunc(() => refFunc)
    }
    setup()
  }, [])

  useEffect(() => {
    if (mounted) {
      state.clearLoading()
    }
  }, [mounted])

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (stripe) {
          if (state.loading) {
            return
          }

          state.wrapPromise(stripe.handleSubmit())
        }
      }}
    >
      <Stack>
        <Box ref={refFunc}></Box>
        <Button type="submit">Pay</Button>
      </Stack>
    </form>
  )
}
