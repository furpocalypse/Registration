import { AuthStore } from "#src/features/auth/stores/AuthStore.js"
import { ConfiguredMiddleware } from "wretch"

/**
 * Get middleware that will retry requests on 401 Unauthorized errors.
 * @param AuthStore - The {@link AuthStore}.
 */
export const getRetryMiddleware =
  (baseURL: URL, authStore: AuthStore): ConfiguredMiddleware =>
  (next) =>
  async (url, opts) => {
    for (;;) {
      // wait for an access token
      const authInfo = await authStore.getAuthInfo()

      // attempt to make the request and catch 401
      const newOpts = setAuthHeader(baseURL, authInfo.accessToken, url, opts)
      const response = await next(url, newOpts)

      if (response.status == 401) {
        await authStore.attemptRefresh(authInfo)
        continue
      } else {
        return response
      }
    }
  }

/**
 * Get a {@link RequestInit} with the Authorization header set.
 * @param baseURL - The base URL of the server.
 * @param accessToken - The access token.
 * @param url - The request URL.
 * @param opts - The current options.
 * @returns Updated {@link RequestInit} options.
 */
export const setAuthHeader = (
  baseURL: URL,
  accessToken: string | null | undefined,
  url: string,
  opts: RequestInit
): RequestInit => {
  const urlObj = new URL(url, window.location.href)

  if (urlObj.origin == baseURL.origin && accessToken) {
    const newHeaders = new Headers(opts.headers)
    newHeaders.set("Authorization", `Bearer ${accessToken}`)
    return { ...opts, headers: newHeaders }
  } else {
    return opts
  }
}
