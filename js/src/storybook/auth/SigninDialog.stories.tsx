import { SigninDialog } from "#src/features/auth/components/SigninDialog.js"
import { Meta, StoryFn } from "@storybook/react"

export default {
  component: SigninDialog,
  parameters: {
    layout: "fullscreen",
  },
} as Meta<typeof SigninDialog>

export const Default: StoryFn<typeof SigninDialog> = (args) => {
  return <SigninDialog {...args} />
}

Default.args = {
  opened: true,
  enabledOptions: {
    email: true,
    guest: true,
  },
}
