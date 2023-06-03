import { placeholderWretch } from "#src/config/api.js"
import { CartStore, CurrentCartStore } from "#src/features/cart/stores.js"
import { createContext, useContext } from "react"

const defaultStore = new CartStore(placeholderWretch)

export const CartStoreContext = createContext(defaultStore)
export const CurrentCartStoreContext = createContext(
  new CurrentCartStore(placeholderWretch, "", defaultStore)
)

export const useCartStore = () => useContext(CartStoreContext)
export const useCurrentCartStore = () => useContext(CurrentCartStoreContext)
