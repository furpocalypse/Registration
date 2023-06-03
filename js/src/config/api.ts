import wretch from "wretch"

/**
 * The default {@link wretch} instance.
 */
export const defaultWretch = wretch()

/**
 * Placeholder {@link wretch} instance.
 */
export const placeholderWretch = wretch().middlewares([
  () => () => {
    throw new Error("The application was not configured")
  },
])
