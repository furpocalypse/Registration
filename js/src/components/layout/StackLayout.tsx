import {
  DefaultProps,
  Selectors,
  Stack,
  StackProps,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"

const useStyles = createStyles(() => ({
  root: {
    flex: "auto",
  },
}))

export type StackLayoutProps = StackProps &
  DefaultProps<Selectors<typeof useStyles>>

export const StackLayout = (props: StackLayoutProps) => {
  const { className, classNames, styles, unstyled, children, ...other } =
    useComponentDefaultProps("StackLayout", {}, props)

  const { classes, cx } = useStyles(undefined, {
    name: "StackLayout",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Stack className={cx(className, classes.root)} {...other}>
      {children}
    </Stack>
  )
}
