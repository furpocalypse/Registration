import {
  ActionIcon,
  Card,
  CardProps,
  DefaultProps,
  Grid,
  Menu,
  Selectors,
  Skeleton,
  SkeletonProps,
  Text,
  Title,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { IconDotsVertical } from "@tabler/icons-react"
import { ReactNode } from "react"

const cardStyles = createStyles({
  root: {},
})

export type RegistrationCardProps = {
  title?: ReactNode
  subtitle?: ReactNode
  menuOptions?: { id: string; label: string }[]
  onMenuSelect?: (id: string) => void
  children?: ReactNode
} & DefaultProps<Selectors<typeof cardStyles>> &
  Omit<CardProps, "styles">

export const RegistrationCard = (props: RegistrationCardProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
    title,
    subtitle,
    menuOptions,
    onMenuSelect,
    children,
    ...other
  } = useComponentDefaultProps("RegistrationCard", { menuOptions: [] }, props)

  const { classes, cx } = cardStyles(undefined, {
    name: "RegistrationCard",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Card
      className={cx(classes.root, className)}
      padding="xs"
      shadow="xs"
      {...other}
    >
      <Grid justify="flex-end" align="flex-start">
        <Grid.Col span="auto" sx={{ minWidth: 0 }}>
          <Title order={3} truncate>
            {title}
          </Title>
          <Text truncate>{subtitle}</Text>
        </Grid.Col>
        {menuOptions.length > 0 && (
          <Grid.Col span="content">
            <Menu withinPortal>
              <Menu.Target>
                <ActionIcon title="Show registration options">
                  <IconDotsVertical />
                </ActionIcon>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>Options</Menu.Label>
                {menuOptions.map((opt) => (
                  <Menu.Item
                    key={opt.id}
                    onClick={() => onMenuSelect && onMenuSelect(opt.id)}
                  >
                    {opt.label}
                  </Menu.Item>
                ))}
              </Menu.Dropdown>
            </Menu>
          </Grid.Col>
        )}
      </Grid>
      {children}
    </Card>
  )
}

const placeholderStyles = createStyles({
  root: {},
})

export type RegistrationCardPlaceholderProps = DefaultProps<
  Selectors<typeof placeholderStyles>
> &
  SkeletonProps

export const RegistrationCardPlaceholder = (
  props: RegistrationCardPlaceholderProps
) => {
  const { className, classNames, styles, unstyled, height, ...other } =
    useComponentDefaultProps(
      "RegistrationCardPlaceholder",
      { height: 150 },
      props
    )

  const { classes, cx } = placeholderStyles(undefined, {
    name: "RegistrationCardPlaceholder",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Skeleton
      className={cx(classes.root, className)}
      height={height}
      {...other}
    />
  )
}
