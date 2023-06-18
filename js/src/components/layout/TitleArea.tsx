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
  },
  title: {},
  subtitle: {},
}))

export type TitleAreaProps = {
  TitleProps?: TitleProps
  SubtitleProps?: TextProps
  ContainerProps?: ContainerProps
} & BoxProps &
  DefaultProps<Selectors<typeof useStyles>>

export const TitleArea = (props: TitleAreaProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
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
