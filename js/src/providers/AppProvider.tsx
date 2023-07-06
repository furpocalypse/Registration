import {
  AccountStoreProvider,
  AuthStoreProvider,
} from "#src/features/auth/providers.js"
import { WretchContext } from "#src/hooks/api.js"
import { AppStoreContext } from "#src/hooks/app.js"
import { useLoader } from "#src/hooks/loader.js"
import { ShowLoadingOverlay } from "#src/routes/LoadingOverlay.js"
import { NotFoundPage } from "#src/routes/NotFoundPage.js"
import { AppStore } from "#src/stores/AppStore.js"
import { ReactNode } from "react"

export const AppProvider = ({ children }: { children?: ReactNode }) => {
  const appStoreLoader = useLoader(() => AppStore.fromConfig())

  return (
    <appStoreLoader.Component
      notFound={<NotFoundPage />}
      placeholder={<ShowLoadingOverlay />}
    >
      {(appStore) => (
        <AppStoreContext.Provider value={appStore}>
          <AuthStoreProvider authStore={appStore.authStore}>
            <AccountStoreProvider>
              <WretchContext.Provider value={appStore.authStore.authWretch}>
                {children}
              </WretchContext.Provider>
            </AccountStoreProvider>
          </AuthStoreProvider>
        </AppStoreContext.Provider>
      )}
    </appStoreLoader.Component>
  )
}
