import wretch from "wretch"

let _defaultWretch = wretch()

// Set the env var DELAY=1000 to add a simulated ~1000ms delay to all fetch requests
if (process.env.DELAY) {
  const delayAmount = parseInt(process.env.DELAY)
  if (!isNaN(delayAmount)) {
    _defaultWretch = _defaultWretch.middlewares([
      (next) => async (url, opts) => {
        const rand = 0.8 + Math.random() * 0.4
        const delay = Math.round(delayAmount * rand)
        await new Promise((r) => window.setTimeout(r, delay))
        return await next(url, opts)
      },
    ])
  }
}

/**
 * The default {@link wretch} instance.
 */
export const defaultWretch = _defaultWretch

/**
 * Placeholder {@link wretch} instance.
 */
export const placeholderWretch = wretch().middlewares([
  () => () => {
    throw new Error("The application was not configured")
  },
])
