import { Header } from "#src/components/layout/Header.js"
import { TitleArea } from "#src/components/layout/TitleArea.js"
import {
  AppShell,
  AppShellProps,
  Box,
  DefaultProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"

const useStyles = createStyles(() => ({
  root: {
    display: "flex",
    flexDirection: "column",
    width: "100%",
    minHeight: "100%",
  },
  appShellMain: {
    paddingLeft: 0,
    paddingRight: 0,
    paddingTop: "3rem",
    display: "flex",
    flexDirection: "column",
    alignItems: "stretch",
  },
  content: {},
}))

export type AppShellLayoutProps = DefaultProps<Selectors<typeof useStyles>> &
  AppShellProps

export const AppShellLayout = (props: AppShellLayoutProps) => {
  const { className, classNames, styles, unstyled, children, ...other } =
    useComponentDefaultProps("AppShellLayout", {}, props)

  const { classes, cx } = useStyles(undefined, {
    name: "AppShellLayout",
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
      <Box className={classes.content}>{children}</Box>
    </AppShell>
  )
}
