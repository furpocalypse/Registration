import { placeholderWretch } from "#src/config/api.js"
import { AuthStore } from "#src/features/auth/stores/AuthStore.js"
import { createContext, useContext } from "react"

export const AuthContext = createContext(
  new AuthStore(placeholderWretch, new URL(window.location.href).origin)
)

export const useAuth = () => useContext(AuthContext)
