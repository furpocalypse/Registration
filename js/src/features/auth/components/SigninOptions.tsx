import {
  Box,
  BoxProps,
  DefaultProps,
  LoadingOverlay,
  NavLink,
  NavLinkProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { IconAt, IconUser } from "@tabler/icons-react"
import { useState } from "react"

export enum SigninOptionType {
  guest = "guest",
  email = "email",
}

type OptionProps = NavLinkProps & { onClick?: () => void }

const EmailOption = (props: OptionProps) => (
  <NavLink
    label="Sign in via email"
    icon={<IconAt />}
    sx={{
      "&:focus": {
        outline: "none",
      },
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

const useStyles = createStyles({
  root: {},
})

/**
 * Sign in options menu.
 */
export type SigninOptionsProps = {
  onSelect?: (type: SigninOptionType) => Promise<void>
  enabledOptions?: Record<SigninOptionType, boolean | undefined>
} & Omit<BoxProps, "children" | "styles"> &
  DefaultProps<Selectors<typeof useStyles>>

export const SigninOptions = (props: SigninOptionsProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
    enabledOptions,
    onSelect,
    ...other
  } = useComponentDefaultProps("SigninOptions", {}, props)

  const { classes, cx } = useStyles(undefined, {
    name: "SigninOptions",
    classNames,
    styles,
    unstyled,
  })

  const [loading, setLoading] = useState(false)

  const handleClick = (type: SigninOptionType) => {
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
    <Box className={cx(classes.root, className)} {...other}>
      {enabledOptions?.email && (
        <EmailOption onClick={() => handleClick(SigninOptionType.email)} />
      )}
      {enabledOptions?.guest && (
        <GuestOption onClick={() => handleClick(SigninOptionType.guest)} />
      )}
      <LoadingOverlay visible={loading} />
    </Box>
  )
}
