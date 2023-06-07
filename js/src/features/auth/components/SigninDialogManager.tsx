import {
  SigninDialog,
  SigninOptions,
} from "#src/features/auth/components/SigninDialog.js"
import { useAuth } from "#src/features/auth/hooks.js"
import { observer } from "mobx-react-lite"

export const SigninDialogManager = observer(() => {
  const auth = useAuth()

  const opened = auth.setupComplete && !auth.checkValid()

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
          const webAuthnAvailable = auth.checkWebAuthnAvailable()
          const platformAuthAvailable = await auth.checkPlatformAuthAvailable()
          if (webAuthnAvailable && platformAuthAvailable) {
            await auth.createWebAuthnAccount()
          } else {
            await auth.createAccount()
          }
        }
      }}
    />
  )
})
