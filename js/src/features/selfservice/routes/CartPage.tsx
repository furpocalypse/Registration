import { Title } from "#src/components/title/Title.js"
import { fetchCartPricingResult } from "#src/features/cart/api.js"
import { useCurrentCartStore } from "#src/features/cart/hooks.js"
import { Cart } from "#src/features/cart/types.js"
import { Cart as CartComponent } from "#src/features/cart/components/Cart.js"
import { useWretch } from "#src/hooks/api.js"
import { LineItem as LineItemComponent } from "#src/features/cart/components/LineItem.js"
import { Modifier as ModifierComponent } from "#src/features/cart/components/Modifier.js"
import { Button, Grid, Stack } from "@mantine/core"
import { IconShoppingCart } from "@tabler/icons-react"
import { useLocation, useNavigate } from "#src/hooks/location.js"
import { observer } from "mobx-react-lite"
import { useLoader } from "#src/hooks/loader.js"
import { Loader } from "#src/util/loader.js"
import { CheckoutMethodsManager } from "#src/features/checkout/components/methods/CheckoutMethodsManager.js"
import { CheckoutManager } from "#src/features/checkout/components/checkout/CheckoutManager.js"
import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { useSelfServiceLoader } from "#src/features/selfservice/hooks.js"

const CartView = observer(
  ({ cartId, eventId }: { cartId: string; eventId: string }) => {
    const wretch = useWretch()
    const loader = useLoader(() => fetchCartPricingResult(wretch, cartId))
    const loc = useLocation()
    const navigate = useNavigate()
    const currentCartStore = useCurrentCartStore()
    const selfService = useSelfServiceLoader()

    const [checkoutComplete, setCheckoutComplete] = useState(false)

    // hacky, redirect on dialog close when checkout is complete
    useEffect(() => {
      if (loc.state?.showCheckoutDialog?.cartId == null && checkoutComplete) {
        currentCartStore.clearCurrentCart()
        navigate(`/events/${eventId}`)
      }
    }, [loc.state?.showCheckoutDialog?.cartId, checkoutComplete])

    const showOptions = () => {
      navigate(loc, {
        state: {
          showCheckoutMethodsDialog: cartId,
        },
      })
    }

    const checkoutAvailable =
      !checkoutComplete &&
      loader.checkLoaded() &&
      loader.value.line_items.length > 0

    return (
      <loader.Component>
        {(result) => (
          <>
            <CartComponent totalPrice={result.total_price}>
              {result.line_items.map((li, i) => (
                <LineItemComponent
                  key={i}
                  onRemove={async () => {
                    const [newId, newCart] =
                      await currentCartStore.cartStore.removeRegistrationFromCart(
                        cartId,
                        li.registration_id
                      )
                    currentCartStore.setCurrentCart(newId, newCart)
                  }}
                  name={li.name}
                  description={li.description}
                  price={li.price}
                  modifiers={li.modifiers.map((m, i) => (
                    <ModifierComponent
                      key={i}
                      name={m.name}
                      amount={m.amount}
                    />
                  ))}
                />
              ))}
            </CartComponent>
            {checkoutAvailable && (
              <Grid>
                <Grid.Col xs={12} sm="content">
                  <Button
                    variant="filled"
                    leftIcon={<IconShoppingCart />}
                    onClick={() => showOptions()}
                  >
                    Checkout
                  </Button>
                </Grid.Col>
              </Grid>
            )}
            <CheckoutMethodsManager cartId={cartId} />
            <CheckoutManager
              cartId={cartId}
              onComplete={() => {
                setCheckoutComplete(true)

                // reload self-service memberships
                selfService.fetch()
              }}
            />
          </>
        )}
      </loader.Component>
    )
  }
)

CartView.displayName = "CartView"

export const CartPage = observer(() => {
  const { eventId = "" } = useParams()
  const currentCartStore = useCurrentCartStore()

  const [cartId, setCartId] = useState<string | null>(null)
  const [cart, setCart] = useState<Loader<Cart> | null>(null)

  useEffect(() => {
    if (currentCartStore.loader && currentCartStore.currentCartId) {
      setCart(currentCartStore.loader)
      setCartId(currentCartStore.currentCartId)
    }
  }, [currentCartStore.loader, currentCartStore.currentCartId])

  if (cartId && cart) {
    return (
      <cart.Component>
        {(_cart) => (
          <Title title="Cart">
            <Stack>
              <CartView key={cartId} cartId={cartId} eventId={eventId} />
            </Stack>
          </Title>
        )}
      </cart.Component>
    )
  } else {
    return null
  }
})

CartPage.displayName = "CartPage"
