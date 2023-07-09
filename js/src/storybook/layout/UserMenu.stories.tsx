import { UserMenu } from "#src/components/layout/UserMenu.js"
import { Meta, StoryFn } from "@storybook/react"

export default {
  component: UserMenu,
} as Meta<typeof UserMenu>

export const Default: StoryFn<typeof UserMenu> = (args) => {
  return <UserMenu {...args} />
}

Default.args = {
  username: "user@test.com",
}
