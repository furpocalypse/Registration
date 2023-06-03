import {
  DefaultProps,
  LoadingOverlay,
  Modal,
  ModalProps,
  NavLink,
  NavLinkProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
  useMantineTheme,
} from "@mantine/core"
import { useMediaQuery } from "@mantine/hooks"
import { IconAt, IconUser } from "@tabler/icons-react"
import { useState } from "react"

export enum SigninOptions {
  guest = "guest",
  email = "email",
}

type OptionProps = NavLinkProps & { onClick?: () => void }

const EmailOption = (props: OptionProps) => (
  <NavLink
    label="Sign in with email"
    icon={<IconAt />}
    sx={{
      outline: "none",
    }}
    {...props}
  />
)

const GuestOption = (props: OptionProps) => (
  <NavLink
    label="Continue as guest"
    description="You might not be able to update your information later"
    icon={<IconUser />}
    sx={{
      "&:focus": {
        outline: "none",
      },
    }}
    {...props}
  />
)

const signinDialogStyles = createStyles({
  root: {},
  body: {
    padding: "0 0 8px 0",
  },
})

export type SigninDialogProps = {
  onSelect?: (type: SigninOptions) => Promise<void>
  enabledOptions?: Record<SigninOptions, boolean | undefined>
} & Omit<
  ModalProps,
  "children" | "styles" | "title" | "fullScreen" | "onClose" | "onSelect"
> &
  DefaultProps<Selectors<typeof signinDialogStyles>>

export const SigninDialog = (props: SigninDialogProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
    enabledOptions,
    onSelect,
    ...other
  } = useComponentDefaultProps("SigninDialog", {}, props)

  const { classes, cx } = signinDialogStyles(undefined, {
    name: "SigninDialog",
    classNames,
    styles,
    unstyled,
  })

  const theme = useMantineTheme()
  const isSmall = useMediaQuery(`(max-width: ${theme.breakpoints.sm})`)
  const [loading, setLoading] = useState(false)

  const handleClick = (type: SigninOptions) => {
    if (loading) {
      return
    }

    if (onSelect) {
      setLoading(true)
      onSelect(type)
        .catch(() => null)
        .then(() => setLoading(false))
    }
  }

  return (
    <Modal
      className={cx(classes.root, className)}
      title="Sign In"
      fullScreen={isSmall}
      classNames={{
        body: classes.body,
      }}
      closeOnClickOutside={false}
      withCloseButton={false}
      onClose={() => null}
      centered
      {...other}
    >
      <LoadingOverlay visible={loading} />
      {enabledOptions?.email && (
        <EmailOption onClick={() => handleClick(SigninOptions.email)} />
      )}
      {enabledOptions?.guest && (
        <GuestOption onClick={() => handleClick(SigninOptions.guest)} />
      )}
    </Modal>
  )
}
