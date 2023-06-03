import React from "react"
import { MantineProvider } from "@mantine/core"
import type { Preview } from "@storybook/react"
import defaultTheme from "../src/config/theme"

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
  },
  decorators: [
    (Story) => {
      return (
        <MantineProvider withGlobalStyles withNormalizeCSS theme={defaultTheme}>
          <Story />
        </MantineProvider>
      )
    },
  ],
}

export default preview
