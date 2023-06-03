import { WretchError } from "wretch"

/**
 * Check if an error is a {@link WretchError}.
 */
export const isWretchError = (e: unknown): e is WretchError => {
  return (
    e != null &&
    typeof e == "object" &&
    "name" in e &&
    "message" in e &&
    "status" in e &&
    "response" in e &&
    "url" in e
  )
}

export const handleNotFound = <T>(promise: Promise<T>): Promise<T | null> => {
  return promise.catch((err) => {
    if (isWretchError(err) && err.status == 404) {
      return null
    }
    return Promise.reject(err)
  })
}
