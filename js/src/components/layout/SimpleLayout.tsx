import { Header } from "#src/components/layout/Header.js"
import { TitleArea } from "#src/components/layout/TitleArea.js"
import {
  AppShell,
  AppShellProps,
  Box,
  Container,
  ContainerProps,
  DefaultProps,
  Selectors,
  Stack,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { ReactNode } from "react"

const layoutStyles = createStyles((theme) => ({
  root: {
    display: "flex",
    flexDirection: "column",
    width: "100%",
    minHeight: "100%",
  },
  appShellMain: {
    paddingLeft: 0,
    paddingRight: 0,
    paddingTop: 48,
    display: "flex",
    flexDirection: "column",
    alignItems: "stretch",
  },
  container: {
    padding: 16,
    flex: "auto",
    display: "flex",
    alignItems: "stretch",
  },
  stack: {
    flex: "auto",
  },
}))

export type SimpleLayoutProps = {
  children?: ReactNode
  ContainerProps?: ContainerProps
} & DefaultProps<Selectors<typeof layoutStyles>> &
  AppShellProps

export const SimpleLayout = (props: SimpleLayoutProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
    children,
    ContainerProps,
    ...other
  } = useComponentDefaultProps("SimpleLayout", {}, props)

  const { classes, cx } = layoutStyles(undefined, {
    name: "SimpleLayout",
    classNames,
    styles,
    unstyled,
  })

  return (
    <AppShell
      header={<Header />}
      className={cx(classes.root, className)}
      classNames={{
        main: classes.appShellMain,
      }}
      {...other}
    >
      <TitleArea />
      <Box>
        <Container size="lg" className={classes.container} {...ContainerProps}>
          <Stack className={classes.stack}>{children}</Stack>
        </Container>
      </Box>
    </AppShell>
  )
}
