import { placeholderWretch } from "#src/config/api.js"
import { createContext, useContext } from "react"

export const WretchContext = createContext(placeholderWretch)

/**
 * Get the configured {@link wretch} object.
 */
export const useWretch = () => useContext(WretchContext)
