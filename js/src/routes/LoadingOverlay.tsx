import {
  Center,
  DefaultProps,
  Loader,
  Overlay,
  OverlayProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
  useMantineTheme,
} from "@mantine/core"
import { action, makeAutoObservable } from "mobx"
import { observer } from "mobx-react-lite"
import { createContext, useContext, useLayoutEffect } from "react"

const loadingPageStyles = createStyles({
  root: {
    display: "flex",
    alignItems: "stretch",
  },
  center: {
    flex: "auto",
  },
})

const LoadingContext = createContext(makeAutoObservable({ loading: 0 }))

export type LoadingOverlayProps = {
  backgroundColor?: string
} & DefaultProps<Selectors<typeof loadingPageStyles>> &
  Omit<OverlayProps, "children">

/**
 * Overlay that covers the screen while loading.
 */
export const LoadingOverlay = observer((props: LoadingOverlayProps) => {
  const theme = useMantineTheme()

  const { className, classNames, styles, unstyled, backgroundColor, ...other } =
    useComponentDefaultProps(
      "LoadingOverlay",
      { backgroundColor: theme.white },
      props
    )

  const { classes, cx } = loadingPageStyles(undefined, {
    name: "LoadingOverlay",
    classNames,
    styles,
    unstyled,
  })

  const context = useContext(LoadingContext)

  const opened = context.loading > 0

  // TODO: transition

  if (!opened) {
    return null
  }

  return (
    <Overlay
      className={cx(classes.root, className)}
      fixed
      color={backgroundColor}
      opacity={1}
      {...other}
    >
      <Center className={classes.center}>
        <Loader variant="dots" />
      </Center>
    </Overlay>
  )
})

LoadingOverlay.displayName = "LoadingOverlay"

/**
 * Kind of a hacky way to the loading overlay by rendering this component as a
 * placeholder.
 */
export const ShowLoadingOverlay = () => {
  const context = useContext(LoadingContext)

  useLayoutEffect(
    action(() => {
      context.loading += 1
      return action(() => {
        context.loading -= 1
      })
    }),
    []
  )

  return null
}
