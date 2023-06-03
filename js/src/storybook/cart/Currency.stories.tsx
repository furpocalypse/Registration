import {
  Currency,
  CurrencyContext,
  CurrencyProps,
} from "#src/features/cart/components/Currency.js"
import { Meta, StoryFn } from "@storybook/react"

export default {
  component: Currency,
  args: {
    amount: 1000,
    currency: "USD",
  },
} as Meta<CurrencyProps & { currency: string }>

export const Default: StoryFn<CurrencyProps & { currency: string }> = (
  args
) => {
  return (
    <CurrencyContext.Provider value={args.currency}>
      <Currency amount={args.amount} />
    </CurrencyContext.Provider>
  )
}
