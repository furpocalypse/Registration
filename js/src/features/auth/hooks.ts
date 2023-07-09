import { placeholderWretch } from "#src/config/api.js"
import { AccountStore } from "#src/features/auth/stores/AccountStore.js"
import { AuthStore } from "#src/features/auth/stores/AuthStore.js"
import { createContext, useContext } from "react"

const defaultAuthStore = new AuthStore(
  new URL(window.location.href),
  placeholderWretch
)

export const AuthContext = createContext(defaultAuthStore)

export const useAuth = () => useContext(AuthContext)

export const AccountStoreContext = createContext(
  new AccountStore(placeholderWretch, defaultAuthStore)
)

export const useAccountStore = () => useContext(AccountStoreContext)
