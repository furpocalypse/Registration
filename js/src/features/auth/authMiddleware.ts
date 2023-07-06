import { AuthStore } from "#src/features/auth/stores/AuthStore.js"
import { when } from "mobx"
import { ConfiguredMiddleware } from "wretch"

/**
 * Get a middleware to set the Authorization header.
 * @param baseURL - The server's base URL.
 * @param authStore - The {@link AuthStore}.
 */
export const getAccessTokenMiddleware =
  (baseURL: URL, authStore: AuthStore): ConfiguredMiddleware =>
  (next) =>
  async (url, opts) => {
    const urlObj = new URL(url, window.location.href)
    if (urlObj.origin == baseURL.origin && authStore.accessToken) {
      const newHeaders = new Headers(opts.headers)
      newHeaders.set("Authorization", `Bearer ${authStore.accessToken}`)
      return await next(url, { ...opts, headers: newHeaders })
    } else {
      return await next(url, opts)
    }
  }

/**
 * Get middleware that will retry requests on 401 Unauthorized errors.
 * @param AuthStore - The {@link AuthStore}.
 */
export const getRetryMiddleware =
  (authStore: AuthStore): ConfiguredMiddleware =>
  (next) =>
  async (url, opts) => {
    for (;;) {
      // wait for an access token
      const accessToken = authStore.accessToken
      if (!accessToken) {
        await when(() => !!authStore.accessToken)
        continue
      }

      // attempt to make the request and catch 401
      const response = await next(url, opts)
      if (response.status == 401) {
        // only call once per token
        if (
          authStore.accessToken == accessToken &&
          authStore.markInvalid(accessToken)
        ) {
          authStore.refresh()
        }

        // wait for valid credentials before retrying
        await when(() => authStore.getIsAuthorized())
        continue
      } else {
        return response
      }
    }
  }
