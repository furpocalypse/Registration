import {
  SubtitlePlaceholder,
  TitlePlaceholder,
} from "#src/components/title/Title.js"
import {
  ActionIcon,
  AppShell,
  AppShellProps,
  Container,
  ContainerProps,
  DefaultProps,
  Header,
  HeaderProps,
  Selectors,
  Stack,
  Text,
  Title,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { IconHome } from "@tabler/icons-react"
import { ComponentType, ReactNode } from "react"

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
    display: "flex",
    alignItems: "stretch",
  },
  header: {
    display: "flex",
    alignItems: "center",
    marginBottom: theme.spacing.md,
  },
  homeIcon: {
    marginLeft: "1rem",
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
  logo?: ComponentType<Record<string, never>> | string
  homeUrl?: string
  HeaderProps?: HeaderProps
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
    logo: Logo,
    homeUrl,
    HeaderProps,
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
    <>
      <AppShell
        header={
          <Header height={48} className={classes.header} {...HeaderProps}>
            <ActionIcon
              className={classes.homeIcon}
              component="a"
              href={homeUrl ?? "/"}
              title="Home"
            >
              {typeof Logo === "function" ? (
                <Logo />
              ) : typeof Logo === "string" ? (
                <img src={Logo} alt="" />
              ) : (
                <IconHome />
              )}
            </ActionIcon>
          </Header>
        }
        className={cx(classes.root, className)}
        classNames={{
          main: classes.appShellMain,
        }}
        {...other}
      >
        <Container size="lg" className={classes.container} {...ContainerProps}>
          <Stack className={classes.stack}>
            <Title order={1}>
              <TitlePlaceholder />
            </Title>
            <Text>
              <SubtitlePlaceholder />
            </Text>
            {children}
          </Stack>
        </Container>
      </AppShell>
    </>
  )
}
