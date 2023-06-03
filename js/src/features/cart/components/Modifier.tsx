import { Currency } from "#src/features/cart/components/Currency.js"
import {
  DefaultProps,
  Group,
  GroupProps,
  Selectors,
  Text,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"

const modifierStyles = createStyles({
  root: {
    textAlign: "right",
    alignItems: "baseline",
  },
  text: {
    textAlign: "right",
    fontSize: "small",
  },
  amount: {
    textAlign: "right",
    fontSize: "small",
    minWidth: 50,
  },
})

export type ModifierProps = {
  name: string
  amount: number
} & Omit<GroupProps, "children"> &
  DefaultProps<Selectors<typeof modifierStyles>>

/**
 * Line item modifier.
 */
export const Modifier = (props: ModifierProps) => {
  const { className, classNames, styles, unstyled, name, amount, ...other } =
    useComponentDefaultProps("Modifier", { position: "right" }, props)

  const { classes, cx } = modifierStyles(undefined, {
    name: "Modifier",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Group className={cx(classes.root, className)} {...other}>
      <Text component="span" className={classes.text}>
        {name}
      </Text>
      <Text component="span" className={classes.amount}>
        <Currency amount={amount} />
      </Text>
    </Group>
  )
}
