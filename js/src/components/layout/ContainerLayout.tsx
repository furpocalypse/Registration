import {
  Container,
  ContainerProps,
  DefaultProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"

const useStyles = createStyles(() => ({
  root: {
    padding: "1rem",
    flex: "auto",
    display: "flex",
    alignItems: "stretch",
  },
}))

export type ContainerLayoutProps = ContainerProps &
  DefaultProps<Selectors<typeof useStyles>>

export const ContainerLayout = (props: ContainerLayoutProps) => {
  const { className, classNames, styles, unstyled, children, ...other } =
    useComponentDefaultProps("ContainerLayout", {}, props)

  const { classes, cx } = useStyles(undefined, {
    name: "ContainerLayout",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Container className={cx(className, classes.root)} size="lg" {...other}>
      {children}
    </Container>
  )
}
