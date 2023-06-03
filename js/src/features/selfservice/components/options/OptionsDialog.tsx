import {
  Button,
  DefaultProps,
  LoadingOverlay,
  Modal,
  ModalProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
  useMantineTheme,
} from "@mantine/core"
import { ModalRootProps } from "@mantine/core/lib/Modal/ModalRoot/ModalRoot.js"
import { useMediaQuery } from "@mantine/hooks"
import { useEffect, useState } from "react"

const modalStyles = createStyles({
  root: {},
  body: {
    // padding: 0
  },
})

export type OptionsDialogProps = {
  title?: string
  options: { id: string; label: string }[]
  onSelect?: (id: string) => Promise<void>
  onClose?: () => void
} & DefaultProps<Selectors<typeof modalStyles>> &
  Omit<ModalRootProps, "children" | "styles" | "onSelect">

export const OptionsDialog = (props: OptionsDialogProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
    title,
    options,
    onSelect,
    opened,
    ...other
  } = useComponentDefaultProps(
    "OptionsDialog",
    { title: "Add Registration" },
    props
  )

  const { classes, cx } = modalStyles(undefined, {
    name: "OptionsDialog",
    classNames,
    styles,
    unstyled,
  })

  const [loading, setLoading] = useState(false)

  // kind of hacky, keep loading state until hidden
  useEffect(() => {
    if (opened) {
      setLoading(false)
    }
  }, [opened])

  const theme = useMantineTheme()
  const breakpoint = theme.breakpoints.md

  const large = useMediaQuery(`(min-width: ${breakpoint})`)

  return (
    <Modal
      title={title}
      centered={large}
      fullScreen={!large}
      className={cx(classes.root, className)}
      classNames={{
        body: classes.body,
      }}
      opened={opened}
      {...other}
    >
      <Button.Group orientation="vertical">
        {options.map((o) => (
          <Button
            key={o.id}
            size="md"
            variant="subtle"
            onClick={() => {
              if (opened && !loading && onSelect) {
                setLoading(true)
                onSelect(o.id).catch(() => {
                  setLoading(false)
                })
              }
            }}
          >
            {o.label}
          </Button>
        ))}
      </Button.Group>
      <LoadingOverlay visible={loading} zIndex={1400} />
    </Modal>
  )
}
