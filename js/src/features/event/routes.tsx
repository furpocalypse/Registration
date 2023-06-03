import { EventStoreProvider } from "#src/features/event/providers.js"
import { Outlet } from "react-router-dom"

export const EventStoreRoute = () => {
  return (
    <EventStoreProvider>
      <Outlet />
    </EventStoreProvider>
  )
}
