import { CheckoutMethod } from "#src/features/checkout/types/Checkout.js"
import {
  Button,
  DefaultProps,
  LoadingOverlay,
  LoadingOverlayProps,
  Modal,
  ModalProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { useEffect, useState } from "react"

const useStyles = createStyles({
  root: {},
  body: {
    minHeight: 100,
  },
})

export type CheckoutMethodsDialogProps = {
  methods: CheckoutMethod[] | Promise<CheckoutMethod[]>
  onSelect?: (service: string, method?: string) => void
  LoadingOverlayProps?: Partial<LoadingOverlayProps>
} & DefaultProps<Selectors<typeof useStyles>> &
  Omit<ModalProps, "styles" | "children" | "onSelect">

export const CheckoutMethodsDialog = (props: CheckoutMethodsDialogProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
    methods,
    onSelect,
    opened,
    LoadingOverlayProps,
    ...other
  } = useComponentDefaultProps(
    "CheckoutMethodsDialog",
    {
      LoadingOverlayProps: {
        zIndex: 1000,
      },
    },
    props
  )

  const { classes, cx } = useStyles(undefined, {
    name: "CheckoutMethodsDialog",
    classNames,
    styles,
    unstyled,
  })

  const [loaded, setLoaded] = useState("then" in methods ? false : true)
  const [methodsArray, setMethodsArray] = useState<CheckoutMethod[]>(
    "then" in methods ? [] : methods
  )

  const showOptions = loaded && methodsArray.length != 1

  useEffect(() => {
    // load the methods
    if (opened && "then" in methods) {
      methods.then((res) => {
        setMethodsArray(res)
        setLoaded(true)
      })
    }
  }, [methods, opened])

  useEffect(() => {
    if (loaded && methodsArray.length == 1) {
      // select the first option automatically if it is the only option
      onSelect && onSelect(methodsArray[0].service, methodsArray[0].method)
    }
  }, [loaded, methodsArray])

  return (
    <Modal
      title="Payment Method"
      centered
      className={cx(classes.root, className)}
      classNames={{
        body: classes.body,
      }}
      opened={opened}
      {...other}
    >
      <Button.Group orientation="vertical">
        {showOptions &&
          methodsArray.map((m) => (
            <Button
              key={`${m.service}-${m.method}`}
              size="md"
              variant="subtle"
              onClick={() => {
                onSelect && onSelect(m.service, m.method)
              }}
            >
              {m.name || "Checkout"}
            </Button>
          ))}
      </Button.Group>
      <LoadingOverlay {...LoadingOverlayProps} visible={!showOptions} />
    </Modal>
  )
}
