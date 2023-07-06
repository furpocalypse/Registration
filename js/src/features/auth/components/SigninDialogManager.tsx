import {
  SigninDialog,
  SigninOptions,
} from "#src/features/auth/components/SigninDialog.js"
import { useAccountStore, useAuth } from "#src/features/auth/hooks.js"
import { observer } from "mobx-react-lite"
import { useEffect, useState } from "react"

export const SigninDialogManager = observer(() => {
  const auth = useAuth()
  const accountStore = useAccountStore()
  const [webAuthnCheckFinished, setWebAuthnCheckFinished] = useState(false)

  // attempt to perform webauthn authentication before showing login options
  useEffect(() => {
    if (auth.loaded && !auth.accessToken && !webAuthnCheckFinished) {
      const webAuthnAvailable = accountStore.checkWebAuthnAvailable()
      const credentialId = accountStore.getSavedWebAuthnCredentialId()

      if (webAuthnAvailable && credentialId) {
        accountStore.performWebAuthnAuthentication().then(() => {
          setWebAuthnCheckFinished(true)
        })
      } else {
        setWebAuthnCheckFinished(true)
      }
    }
  }, [auth.loaded, auth.accessToken, webAuthnCheckFinished])

  const opened = auth.loaded && !auth.accessToken && webAuthnCheckFinished

  return (
    <SigninDialog
      opened={opened}
      enabledOptions={{
        email: false,
        guest: true,
      }}
      onSelect={async (type) => {
        // TODO: handle differently?
        if (type == SigninOptions.guest) {
          const webAuthnAvailable = accountStore.checkWebAuthnAvailable()
          const platformAuthAvailable = webAuthnAvailable
            ? await accountStore.checkPlatformAuthAvailable()
            : false
          if (webAuthnAvailable && platformAuthAvailable) {
            const hasCredential = accountStore.getSavedWebAuthnCredentialId()

            if (hasCredential) {
              // sign in
              const authResult =
                await accountStore.performWebAuthnAuthentication()
              if (authResult) {
                return
              }
            }

            // attempt to register
            const createResult = await accountStore.createWebAuthnAccount()
            if (createResult) {
              return
            }
          }

          // create a normal account if the above steps failed
          await accountStore.createNewAccount()
        }
      }}
    />
  )
})
