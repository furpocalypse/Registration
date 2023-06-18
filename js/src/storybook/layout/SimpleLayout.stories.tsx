import { SimpleLayout } from "#src/components/layout/SimpleLayout.js"
import { Subtitle, Title } from "#src/components/title/Title.js"
import { Meta, StoryFn } from "@storybook/react"

type Args = {
  noLogo: boolean
}

export default {
  component: SimpleLayout,
  parameters: {
    layout: "fullscreen",
  },
  args: {
    noLogo: false,
  },
} as Meta<Args>

export const Default: StoryFn<Args> = (args) => (
  <SimpleLayout
    AppShellLayoutProps={{
      TitleAreaProps: {
        noLogo: args.noLogo,
      },
    }}
  >
    <Title title="Example Page">
      <Subtitle subtitle="Example subtitle">Page content</Subtitle>
    </Title>
  </SimpleLayout>
)
