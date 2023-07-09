import { EmailAuth } from "#src/features/auth/components/EmailAuth.js"
import { SigninDialog } from "#src/features/auth/components/SigninDialog.js"
import {
  SigninOptionType,
  SigninOptions,
} from "#src/features/auth/components/SigninOptions.js"
import { useAccountStore, useAuth } from "#src/features/auth/hooks.js"
import { useNavigate } from "#src/hooks/location.js"
import { useLocation } from "#src/hooks/location.js"
import { isWretchError } from "#src/util/api.js"
import { observer } from "mobx-react-lite"
import { useState } from "react"

declare module "#src/hooks/location.js" {
  interface LocationState {
    showEmailAuth?: boolean
  }
}

/**
 * Manages sign-in dialog and state.
 */
export const SigninDialogManager = observer(() => {
  const auth = useAuth()
  const accountStore = useAccountStore()
  const loc = useLocation()
  const navigate = useNavigate()

  const [email, setEmail] = useState("")

  // only show after initial setup completes, and if there is no access token.
  // also hide if the email auth modal is open.
  const opened = accountStore.initialSetupComplete && !auth.accessToken

  const showEmailAuth = !!loc.state?.showEmailAuth
  const showOptions = !showEmailAuth

  let content

  if (showOptions) {
    content = (
      <SigninOptions
        enabledOptions={{
          email: true,
          guest: true,
        }}
        onSelect={async (type) => {
          if (!opened) {
            return
          }

          if (type == SigninOptionType.guest) {
            await accountStore.createAccount()
          } else if (type == SigninOptionType.email) {
            // show email auth dialog
            setEmail("")
            navigate(loc, { state: { ...loc.state, showEmailAuth: true } })
          }
        }}
      />
    )
  } else if (showEmailAuth) {
    content = (
      <EmailAuth
        email={email || null}
        onSubmit={async (enteredEmail) => {
          if (!opened) {
            return false
          }

          try {
            await accountStore.sendVerificationEmail(enteredEmail)
            setEmail(enteredEmail)
            return true
          } catch (err) {
            if (isWretchError(err) && err.status == 422) {
              return false
            } else {
              throw err
            }
          }
        }}
        onVerify={async (enteredEmail, code) => {
          if (!opened) {
            return false
          }

          const result = await accountStore.verifyEmail(enteredEmail, code)
          if (result) {
            await accountStore.createAccount({ emailToken: result })
            navigate(-1)
            setEmail("")
            return true
          } else {
            return false
          }
        }}
      />
    )
  }

  return <SigninDialog opened={opened}>{content}</SigninDialog>
})
