import { Currency } from "#src/features/cart/components/Currency.js"
import {
  Button,
  DefaultProps,
  Grid,
  Selectors,
  Stack,
  Text,
  Title,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { ReactNode } from "react"

const lineItemStyles = createStyles({
  root: {},
  name: {
    fontWeight: "bold",
    fontSize: "large",
  },
  price: {
    fontWeight: "bold",
    fontSize: "large",
  },
  description: {},
})

export type LineItemProps = {
  name: string
  description?: string
  price: number
  modifiers?: ReactNode[]
  onRemove?: () => void
} & DefaultProps<Selectors<typeof lineItemStyles>>

export const LineItem = (props: LineItemProps) => {
  const {
    name,
    description,
    price,
    modifiers,
    onRemove,
    className,
    classNames,
    styles,
    unstyled,
    ...other
  } = useComponentDefaultProps("LineItem", {}, props)

  const { classes, cx } = lineItemStyles(undefined, {
    name: "LineItem",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Stack className={cx(classes.root, className)} spacing={0} {...other}>
      <Grid align="baseline">
        <Grid.Col span="auto">
          <Title order={4} className={classes.name}>
            {name}
          </Title>
        </Grid.Col>
        <Grid.Col span="content">
          <Text component="span" className={classes.price}>
            <Currency amount={price} />
          </Text>
        </Grid.Col>
      </Grid>
      <Grid>
        <Grid.Col xs={12} sm="auto" order={2} orderSm={1}>
          {description && (
            <Text component="p" className={classes.description}>
              {description}
            </Text>
          )}
        </Grid.Col>
        <Grid.Col xs={12} sm="content" order={1} orderSm={2}>
          {modifiers && modifiers.length > 0 && (
            <Stack spacing={0}>{modifiers}</Stack>
          )}
        </Grid.Col>
      </Grid>
      {onRemove && (
        <Grid>
          <Grid.Col span={12}>
            <Button variant="subtle" color="red" compact onClick={onRemove}>
              Remove
            </Button>
          </Grid.Col>
        </Grid>
      )}
    </Stack>
  )
}
