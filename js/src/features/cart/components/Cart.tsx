import { Currency } from "#src/features/cart/components/Currency.js"
import {
  DefaultProps,
  Divider,
  Grid,
  Group,
  Selectors,
  Skeleton,
  SkeletonProps,
  Stack,
  StackProps,
  Text,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { Fragment, ReactNode } from "react"

const cartStyles = createStyles({
  root: {},
  totalText: {
    textAlign: "right",
    fontWeight: "bold",
  },
  total: {
    textAlign: "right",
    fontWeight: "bold",
    fontSize: "x-large",
  },
})

export type CartProps = {
  children?: ReactNode[]
  totalPrice: number
} & DefaultProps<Selectors<typeof cartStyles>>

export const Cart = (props: CartProps) => {
  const {
    className,
    classNames,
    styles,
    unstyled,
    children,
    totalPrice,
    ...other
  } = useComponentDefaultProps("Cart", {}, props)

  const { classes, cx } = cartStyles(undefined, {
    name: "Cart",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Stack className={cx(classes.root, className)} {...other}>
      {children &&
        children.map((c, i) => (
          <Fragment key={i}>
            {c}
            <Divider />
          </Fragment>
        ))}
      <Grid justify="flex-end">
        <Grid.Col span="content">
          <Group align="baseline">
            <Text component="span" className={classes.totalText}>
              Total
            </Text>
            <Text component="span" className={classes.total}>
              <Currency amount={totalPrice} />
            </Text>
          </Group>
        </Grid.Col>
      </Grid>
    </Stack>
  )
}

const placeholderStyles = createStyles({
  root: {},
  skeleton: {},
})

export type CartPlaceholderProps = {
  SkeletonProps?: Partial<SkeletonProps>
} & DefaultProps<Selectors<typeof placeholderStyles>> &
  StackProps

export const CartPlaceholder = (props: CartPlaceholderProps) => {
  const { className, classNames, styles, unstyled, SkeletonProps, ...other } =
    useComponentDefaultProps(
      "CartPlaceholder",
      {
        SkeletonProps: {
          height: 100,
        },
      },
      props
    )

  const { classes, cx } = placeholderStyles(undefined, {
    name: "CartPlaceholder",
    classNames,
    styles,
    unstyled,
  })

  return (
    <Stack className={cx(classes.root, className)} {...other}>
      <Skeleton className={classes.skeleton} {...SkeletonProps} />
      <Divider />
      <Skeleton className={classes.skeleton} {...SkeletonProps} />
      <Divider />
    </Stack>
  )
}
