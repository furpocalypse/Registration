import {
  DefaultProps,
  Modal,
  ModalProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
  useMantineTheme,
} from "@mantine/core"
import { useMediaQuery } from "@mantine/hooks"

const useStyles = createStyles({
  root: {},
  body: {
    padding: "0 0 8px 0",
  },
})

export type SigninDialogProps = Omit<
  ModalProps,
  "styles" | "fullScreen" | "onClose"
> &
  DefaultProps<Selectors<typeof useStyles>>

/**
 * Sign in dialog component.
 */
export const SigninDialog = (props: SigninDialogProps) => {
  const { className, classNames, styles, unstyled, title, children, ...other } =
    useComponentDefaultProps(
      "SigninDialog",
      {
        title: "Sign In",
      },
      props
    )

  const { classes, cx } = useStyles(undefined, {
    name: "SigninDialog",
    classNames,
    styles,
    unstyled,
  })

  const theme = useMantineTheme()
  const isSmall = useMediaQuery(`(max-width: ${theme.breakpoints.sm})`)

  return (
    <Modal
      className={cx(classes.root, className)}
      title={title}
      fullScreen={isSmall}
      classNames={{
        body: classes.body,
      }}
      closeOnClickOutside={false}
      withCloseButton={false}
      onClose={() => null}
      centered
      {...other}
    >
      {children}
    </Modal>
  )
}
