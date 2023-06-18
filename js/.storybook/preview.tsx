import React from "react"
import type { Preview } from "@storybook/react"
import { ThemeProvider } from "../src/storybook/Utils"

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
        <ThemeProvider>
          <Story />
        </ThemeProvider>
      )
    },
  ],
}

export default preview
