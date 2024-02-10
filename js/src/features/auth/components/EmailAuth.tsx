import {
  Button,
  DefaultProps,
  LoadingOverlay,
  Selectors,
  Stack,
  Text,
  TextInput,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { useState } from "react"

const useStyles = createStyles({
  root: {
    padding: "1rem",
  },
  stack: {},
})

export type EmailAuthProps = {
  email?: string | null
  onSubmit?: (email: string) => Promise<boolean>
  onVerify?: (email: string, code: string) => Promise<boolean>
} & DefaultProps<Selectors<typeof useStyles>>

/**
 * Email auth input.
 */
export const EmailAuth = (props: EmailAuthProps) => {
  const { className, classNames, styles, unstyled, email, onSubmit, onVerify } =
    useComponentDefaultProps("EmailAuth", {}, props)

  const { classes, cx } = useStyles(undefined, {
    name: "EmailAuth",
    classNames,
    styles,
    unstyled,
  })

  const [loading, setLoading] = useState(false)
  const [emailInput, setEmailInput] = useState("")
  const [code, setCode] = useState("")
  const [error, setError] = useState<string | null>(null)

  if (email) {
    // code input
    return (
      <form
        className={cx(classes.root, className)}
        onSubmit={(e) => {
          e.preventDefault()
          if (!code || !onVerify) {
            return
          }

          setLoading(true)
          onVerify(email, code)
            .then((res) => {
              if (res) {
                setError(null)
              } else {
                setError("Try again")
              }
              setLoading(false)
            })
            .catch((e) => {
              setError("Try again")
              setLoading(false)
              throw e
            })
        }}
      >
        <Stack className={classes.stack}>
          <Text>
            We&apos;ve sent a code to your email address. Enter the code below.
          </Text>
          <TextInput
            key="code"
            inputMode="numeric"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            error={error ?? undefined}
            label="Code"
          />
          <Button type="submit">Verify</Button>
        </Stack>
        <LoadingOverlay visible={loading} />
      </form>
    )
  } else {
    return (
      <form
        className={classes.root}
        onSubmit={(e) => {
          e.preventDefault()
          if (!emailInput || !onSubmit) {
            return
          }

          setLoading(true)
          onSubmit(emailInput)
            .then((res) => {
              if (res) {
                setCode("")
                setError(null)
              } else {
                setError("Invalid email")
              }
              setLoading(false)
            })
            .catch((e) => {
              setLoading(false)
              throw e
            })
        }}
      >
        <Stack className={classes.stack}>
          <Text>Enter your email address.</Text>
          <TextInput
            key="email"
            inputMode="email"
            autoComplete="email"
            value={emailInput}
            onChange={(e) => setEmailInput(e.target.value)}
            error={error ?? undefined}
            label="Email"
          />
          <Button type="submit">Continue</Button>
        </Stack>
        <LoadingOverlay visible={loading} />
      </form>
    )
  }
}
