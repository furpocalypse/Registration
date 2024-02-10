import { UserMenu } from "#src/components/layout/UserMenu.js"
import { useAuth } from "#src/features/auth/hooks.js"
import {
  ActionIcon,
  ActionIconProps,
  Box,
  DefaultProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import {
  Header as MantineHeader,
  HeaderProps as MantineHeaderProps,
} from "@mantine/core"
import { IconHome } from "@tabler/icons-react"
import { observer } from "mobx-react-lite"
import { ComponentType, ReactNode } from "react"

const useStyles = createStyles((theme) => ({
  root: {
    display: "flex",
    alignItems: "center",
    paddingLeft: "1rem",
    paddingRight: "1rem",
    background: theme.fn.primaryColor(),
    borderBottom: `${theme.fn.lighten(theme.fn.primaryColor(), 0.2)} solid 1px`,
    color: theme.white,
  },
  homeIcon: {
    color: "inherit",
  },
  content: {
    flex: "auto",
  },
}))

export type HeaderProps = {
  homeUrl?: string
  homeIcon?: ComponentType<Record<string, never>> | string
  ActionIconProps?: ActionIconProps
  children?: ReactNode
} & Omit<MantineHeaderProps, "height" | "children" | "styles"> &
  DefaultProps<Selectors<typeof useStyles>>

export const Header = observer((props: HeaderProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
    homeUrl,
    homeIcon: HomeIcon,
    ActionIconProps,
    children,
    ...other
  } = useComponentDefaultProps("Header", {}, props)

  const { classes, cx } = useStyles(undefined, {
    name: "Header",
    styles,
    unstyled,
    classNames,
  })

  const authStore = useAuth()

  let userMenu

  if (authStore.accessToken) {
    userMenu = (
      <UserMenu
        username={authStore.email || "Guest"}
        onSignOut={() => {
          authStore.setAuthInfo(null)
        }}
      />
    )
  }

  return (
    <MantineHeader
      className={cx(classes.root, className)}
      height={{
        base: "3rem",
      }}
      fixed
      {...other}
    >
      <ActionIcon
        className={classes.homeIcon}
        variant="transparent"
        component="a"
        href={homeUrl ?? "/"}
        title="Home"
        {...ActionIconProps}
      >
        {typeof HomeIcon === "function" ? (
          <HomeIcon />
        ) : typeof HomeIcon === "string" ? (
          <img src={HomeIcon} alt="" />
        ) : (
          <IconHome />
        )}
      </ActionIcon>
      <Box className={classes.content}>{children}</Box>
      {userMenu}
    </MantineHeader>
  )
})

Header.displayName = "Header"
