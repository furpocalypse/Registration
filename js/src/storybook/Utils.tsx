import { MantineProvider } from "@mantine/core"
import theme from "#src/config/theme.js"
import { ReactNode } from "react"

/**
 * Story decorator to provide the configured theme.
 *
 * Defining this in preview.tsx will not respect the webpack overridden import
 * resolution.
 */
export const ThemeProvider = ({ children }: { children?: ReactNode }) => {
  return (
    <MantineProvider theme={theme} withGlobalStyles withNormalizeCSS>
      {children}
    </MantineProvider>
  )
}
