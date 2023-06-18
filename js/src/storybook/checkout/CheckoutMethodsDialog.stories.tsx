import { CheckoutMethodsDialog } from "#src/features/checkout/components/methods/CheckoutMethodsDialog.js"
import { createLoader } from "#src/util/loader.js"
import { Meta, StoryFn } from "@storybook/react"

export default {
  component: CheckoutMethodsDialog,
  args: {
    opened: true,
    methods: [
      { service: "stripe", method: "card", name: "Card" },
      { service: "stripe", method: "google-pay", name: "Google Pay" },
      { service: "system", method: "cash", name: "Cash" },
    ],
  },
  parameters: {
    layout: "fullscreen",
  },
} as Meta<typeof CheckoutMethodsDialog>

export const Default: StoryFn<typeof CheckoutMethodsDialog> = (args) => {
  return <CheckoutMethodsDialog {...args} />
}

export const With_Promise: StoryFn<typeof CheckoutMethodsDialog> = (args) => {
  const { methods, ...other } = args
  return (
    <CheckoutMethodsDialog
      {...other}
      methods={createLoader(() =>
        new Promise((r) => window.setTimeout(r, 1000)).then(() => methods)
      )}
    />
  )
}

export const Auto_Select: StoryFn<typeof CheckoutMethodsDialog> = (args) => {
  return (
    <CheckoutMethodsDialog
      {...args}
      methods={createLoader(() =>
        new Promise((r) => window.setTimeout(r, 1000)).then(() => [
          { service: "mock", name: "Default" },
        ])
      )}
    />
  )
}
