import {
  Anchor,
  AnchorProps,
  DefaultProps,
  Menu,
  MenuProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { IconLogout } from "@tabler/icons-react"

const useStyles = createStyles({
  anchor: {
    color: "inherit",
    fontSize: "small",
  },
})

export type UserMenuProps = {
  username?: string | null
  onSignOut?: () => void
  AnchorProps?: Partial<AnchorProps>
} & Omit<MenuProps, "children" | "styles"> &
  DefaultProps<Selectors<typeof useStyles>>

export const UserMenu = (props: UserMenuProps) => {
  const {
    classNames,
    styles,
    unstyled,
    username,
    onSignOut,
    AnchorProps,
    ...other
  } = useComponentDefaultProps("UserMenu", {}, props)

  const { classes } = useStyles(undefined, {
    name: "UserMenu",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Menu shadow="sm" {...other}>
      <Menu.Target>
        <Anchor
          className={classes.anchor}
          component="button"
          aria-label="User options"
          {...AnchorProps}
        >
          {username}
        </Anchor>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Label>Options</Menu.Label>
        <Menu.Item icon={<IconLogout />} onClick={onSignOut}>
          Sign Out
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  )
}
