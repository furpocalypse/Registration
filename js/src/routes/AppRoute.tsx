import { AppProvider } from "#src/providers/AppProvider.js"
import { Outlet } from "react-router-dom"

export const AppRoute = () => (
  <AppProvider>
    <Outlet />
  </AppProvider>
)
