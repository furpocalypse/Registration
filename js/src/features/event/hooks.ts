import { placeholderWretch } from "#src/config/api.js"
import { EventStore } from "#src/features/event/stores.js"
import { createContext, useContext } from "react"

export const EventStoreContext = createContext(
  new EventStore(placeholderWretch)
)

export const useEvents = () => useContext(EventStoreContext)
