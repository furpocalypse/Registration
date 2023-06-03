import { CartCheckoutState } from "#src/features/checkout/CartCheckoutState.js"
import { CheckoutContainer } from "#src/features/checkout/components/checkout/CheckoutContainer.js"
import { CheckoutDialog } from "#src/features/checkout/components/checkout/CheckoutDialog.js"
import { PaymentServiceID } from "#src/features/checkout/types/Checkout.js"
import { useWretch } from "#src/hooks/api.js"
import { useLocation, useNavigate } from "#src/hooks/location.js"
import { observer, useLocalObservable } from "mobx-react-lite"
import { useEffect } from "react"

declare module "#src/hooks/location.js" {
  interface LocationState {
    showCheckoutDialog?: {
      cartId: string
      service: PaymentServiceID
      method?: string
    }
  }
}

export type CheckoutManagerProps = {
  cartId: string
  onComplete?: (id: string) => void
}

export const CheckoutManager = observer(
  ({ cartId, onComplete }: CheckoutManagerProps) => {
    // const [state, setState] = useState<CartCheckoutState|null>(null)
    const wretch = useWretch()

    const state = useLocalObservable(
      () =>
        new CartCheckoutState(
          cartId,
          CartCheckoutState.defaultStateFactory(wretch),
          // hazard: onComplete is closed over
          onComplete
        )
    )

    const loc = useLocation()
    const navigate = useNavigate()

    const locCart = loc.state?.showCheckoutDialog?.cartId
    const service = loc.state?.showCheckoutDialog?.service
    const method = loc.state?.showCheckoutDialog?.method

    useEffect(() => {
      if (service) {
        state.create(cartId, service, method)
      }
    }, [service, method])

    const show = locCart == cartId

    const LoadingOverlayProps = {
      zIndex: 1000,
    }

    return (
      <CheckoutDialog
        opened={show}
        onClose={() => {
          navigate(-1)
        }}
      >
        {state.checkout && (
          <CheckoutContainer
            state={state.checkout}
            onClose={() => {
              navigate(-1)
            }}
            LoadingOverlayProps={LoadingOverlayProps}
          />
        )}
      </CheckoutDialog>
    )
  }
)

CheckoutManager.displayName = "CheckoutManager"
