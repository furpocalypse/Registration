import { AuthContext } from "#src/features/auth/hooks.js"
import { AuthStore } from "#src/features/auth/stores/AuthStore.js"
import { ReactNode } from "react"

export const AuthStoreProvider = ({
  children,
  authStore,
}: {
  children?: ReactNode
  authStore: AuthStore
}) => {
  return (
    <AuthContext.Provider value={authStore}>{children}</AuthContext.Provider>
  )
}
