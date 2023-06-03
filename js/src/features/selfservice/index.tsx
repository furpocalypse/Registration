import { makeApp } from "#src/util/react.js"
import { RouterProvider } from "react-router-dom"
import { router } from "#src/features/selfservice/routes/Router.js"
import { MantineProvider } from "@mantine/core"
import theme from "#src/config/theme.js"

makeApp(() => (
  <MantineProvider theme={theme} withGlobalStyles withNormalizeCSS>
    <RouterProvider router={router} />
  </MantineProvider>
))
