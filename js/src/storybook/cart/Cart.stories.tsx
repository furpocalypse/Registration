import { Cart, CartPlaceholder } from "#src/features/cart/components/Cart.js"
import { LineItem } from "#src/features/cart/components/LineItem.js"
import { Modifier } from "#src/features/cart/components/Modifier.js"
import { Container } from "@mantine/core"

export default {
  title: "cart/Cart",
  args: {
    editable: true,
  },
}

export const Default = ({ editable }: { editable: boolean }) => {
  const onRemove = editable
    ? () => {
        /* */
      }
    : undefined
  return (
    <Container size="md">
      <Cart totalPrice={7000}>
        {[
          <LineItem
            key="item1"
            name="Item 1"
            price={2000}
            description="Description of item 1."
            onRemove={onRemove}
            modifiers={[
              <Modifier key="mod1" name="Extra Addon" amount={1000} />,
              <Modifier key="mod2" name="Early Bird Discount" amount={-500} />,
            ]}
          />,
          <LineItem
            key="item2"
            name="Item 2"
            price={3000}
            description="Description of item 2."
            onRemove={onRemove}
          />,
          <LineItem
            key="item3"
            name="Item 3"
            price={1500}
            description="Description of item 3."
            onRemove={onRemove}
          />,
        ]}
      </Cart>
    </Container>
  )
}

export const Placeholder = () => (
  <Container size="md">
    <CartPlaceholder />
  </Container>
)
