import { Logo, LogoProps } from "#src/components/layout/Logo.js"
import {
  SubtitlePlaceholder,
  TitlePlaceholder,
} from "#src/components/title/Title.js"
import {
  Box,
  BoxProps,
  Container,
  ContainerProps,
  DefaultProps,
  Selectors,
  Text,
  TextProps,
  Title,
  TitleProps,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"

const useStyles = createStyles((theme) => ({
  root: {
    background: theme.fn.primaryColor(),
    color: theme.white,
    minHeight: 150,
    display: "flex",
    alignItems: "center",
  },
  container: {
    flex: "auto",
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    paddingTop: "1rem",
    paddingBottom: "1rem",
  },
  logo: {
    flex: "0 0 0",
    marginBottom: "2rem",
  },
  title: {
    fontSize: "1.25rem",
    lineHeight: "2rem",
  },
  subtitle: {
    fontSize: "1rem",
    lineHeight: "1.5rem",
  },
}))

export type TitleAreaProps = {
  noLogo?: boolean
  LogoProps?: LogoProps
  TitleProps?: TitleProps
  SubtitleProps?: TextProps
  ContainerProps?: ContainerProps
} & Omit<BoxProps, "styles"> &
  DefaultProps<Selectors<typeof useStyles>>

export const TitleArea = (props: TitleAreaProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
    noLogo,
    LogoProps,
    TitleProps,
    SubtitleProps,
    ContainerProps,
    ...other
  } = useComponentDefaultProps("TitleArea", {}, props)

  const { classes, cx } = useStyles(undefined, {
    name: "TitleArea",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Box className={cx(classes.root, className)} {...other}>
      <Container className={classes.container} size="lg" {...ContainerProps}>
        {!noLogo && <Logo classNames={{ root: classes.logo }} {...LogoProps} />}
        <Title order={1} className={classes.title} {...TitleProps}>
          <TitlePlaceholder />
        </Title>
        <Text className={classes.subtitle} {...SubtitleProps}>
          <SubtitlePlaceholder />
        </Text>
      </Container>
    </Box>
  )
}
