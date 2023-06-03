import {
  CartStoreContext,
  CurrentCartStoreContext,
  useCartStore,
} from "#src/features/cart/hooks.js"
import { CartStore, CurrentCartStore } from "#src/features/cart/stores.js"
import { useWretch } from "#src/hooks/api.js"
import { ReactNode, useState } from "react"

export const CartStoreProvider = ({ children }: { children?: ReactNode }) => {
  const wretch = useWretch()
  const [cartStore] = useState(() => new CartStore(wretch))

  return (
    <CartStoreContext.Provider value={cartStore}>
      {children}
    </CartStoreContext.Provider>
  )
}

export const CurrentCartStoreProvider = ({
  children,
  eventId,
}: {
  children?: ReactNode
  eventId: string
}) => {
  const wretch = useWretch()
  const cartStore = useCartStore()
  const [currentCartStore] = useState(
    () => new CurrentCartStore(wretch, eventId, cartStore)
  )

  return (
    <CurrentCartStoreContext.Provider value={currentCartStore}>
      {children}
    </CurrentCartStoreContext.Provider>
  )
}
