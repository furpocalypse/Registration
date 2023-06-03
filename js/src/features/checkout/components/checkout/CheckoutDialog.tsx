import {
  DefaultProps,
  Modal,
  ModalProps,
  Selectors,
  Stack,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { ReactNode } from "react"

const useStyles = createStyles({
  root: {},
  body: {
    minHeight: 100,
  },
})

export type CheckoutDialogProps = {
  children?: ReactNode
} & DefaultProps<Selectors<typeof useStyles>> &
  Omit<ModalProps, "styles" | "children">

export const CheckoutDialog = (props: CheckoutDialogProps) => {
  const { className, classNames, styles, unstyled, children, ...other } =
    useComponentDefaultProps("CheckoutDialog", {}, props)

  const { classes, cx } = useStyles(undefined, {
    name: "CheckoutDialog",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Modal
      title="Checkout"
      centered
      className={cx(classes.root, className)}
      classNames={{
        body: classes.body,
      }}
      {...other}
    >
      <Stack>{children}</Stack>
    </Modal>
  )
}
