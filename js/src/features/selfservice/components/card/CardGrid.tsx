import {
  DefaultProps,
  Group,
  Selectors,
  SimpleGrid,
  SimpleGridProps,
  Text,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { IconAlertCircle } from "@tabler/icons-react"
import { ReactNode } from "react"

const gridStyles = createStyles({
  root: {},
})

export type CardGridProps = {
  children?: ReactNode[]
} & DefaultProps<Selectors<typeof gridStyles>> &
  SimpleGridProps

export const CardGrid = (props: CardGridProps) => {
  const { className, classNames, styles, unstyled, children, ...other } =
    useComponentDefaultProps("CardGrid", { children: [] }, props)

  const { classes, cx } = gridStyles(undefined, {
    name: "CardGrid",
    classNames,
    styles,
    unstyled,
  })

  return (
    <SimpleGrid
      className={cx(classes.root, className)}
      spacing="sm"
      cols={1}
      breakpoints={
        children.length > 0
          ? [
              { minWidth: "xs", cols: 1 },
              { minWidth: "sm", cols: 2 },
              { minWidth: "md", cols: 3 },
            ]
          : undefined
      }
      {...other}
    >
      {children.length > 0 ? (
        children
      ) : (
        <Text color="dimmed">
          <Group align="center">
            <IconAlertCircle />
            <Text span inline>
              You have no registrations for this event.
            </Text>
          </Group>
        </Text>
      )}
    </SimpleGrid>
  )
}
