import { Logo } from "#src/components/layout/Logo.js"
import { Box } from "@mantine/core"
import { Meta, StoryFn } from "@storybook/react"

export default {
  component: Logo,
  parameters: {
    layout: "fullscreen",
  },
} as Meta<typeof Logo>

export const Default: StoryFn<typeof Logo> = (args: { alt?: string }) => (
  <Box
    sx={(theme) => ({
      padding: "2rem",
      background: theme.fn.primaryColor(),
    })}
  >
    <Logo {...args} />
  </Box>
)
