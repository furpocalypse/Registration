import { fetchAvailableCheckoutMethods } from "#src/features/cart/api.js"
import { CheckoutMethodsDialog } from "#src/features/checkout/components/methods/CheckoutMethodsDialog.js"
import { PaymentServiceID } from "#src/features/checkout/types/Checkout.js"
import { useWretch } from "#src/hooks/api.js"
import { useLoader } from "#src/hooks/loader.js"
import { useLocation, useNavigate } from "#src/hooks/location.js"

declare module "#src/hooks/location.js" {
  interface LocationState {
    showCheckoutMethodsDialog?: string
  }
}

export type CheckoutMethodsManagerProps = {
  cartId: string
}

export const CheckoutMethodsManager = ({
  cartId,
}: CheckoutMethodsManagerProps) => {
  const wretch = useWretch()
  const options = useLoader(() => fetchAvailableCheckoutMethods(wretch, cartId))

  const loc = useLocation()
  const navigate = useNavigate()

  return (
    <CheckoutMethodsDialog
      opened={loc.state?.showCheckoutMethodsDialog == cartId}
      onClose={() => navigate(-1)}
      methods={options}
      onSelect={(service, method) => {
        navigate(loc, {
          state: {
            showCheckoutDialog: {
              cartId: cartId,
              service: service as PaymentServiceID,
              method: method,
            },
          },
          replace: true,
        })
      }}
    />
  )
}
