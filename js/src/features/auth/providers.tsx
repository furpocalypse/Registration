import {
  AccountStoreContext,
  AuthContext,
  useAuth,
} from "#src/features/auth/hooks.js"
import { AccountStore } from "#src/features/auth/stores/AccountStore.js"
import { AuthStore } from "#src/features/auth/stores/AuthStore.js"
import { ReactNode, useState } from "react"

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

export const AccountStoreProvider = ({
  children,
}: {
  children?: ReactNode
}) => {
  const authStore = useAuth()
  const [accountStore] = useState(
    () => new AccountStore(authStore.wretch, authStore)
  )

  return (
    <AccountStoreContext.Provider value={accountStore}>
      {children}
    </AccountStoreContext.Provider>
  )
}
