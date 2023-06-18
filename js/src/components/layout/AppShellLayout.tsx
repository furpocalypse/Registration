import { Header } from "#src/components/layout/Header.js"
import { TitleArea, TitleAreaProps } from "#src/components/layout/TitleArea.js"
import {
  AppShell,
  AppShellProps,
  Box,
  DefaultProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { ReactNode } from "react"

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

export type AppShellLayoutProps = {
  children?: ReactNode
  TitleAreaProps?: TitleAreaProps
} & DefaultProps<Selectors<typeof useStyles>> &
  Omit<AppShellProps, "children" | "styles">

export const AppShellLayout = (props: AppShellLayoutProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
    children,
    TitleAreaProps,
    ...other
  } = useComponentDefaultProps("AppShellLayout", {}, props)

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
      <TitleArea {...TitleAreaProps} />
      <Box className={classes.content}>{children}</Box>
    </AppShell>
  )
}
