import { action, makeAutoObservable, runInAction, when } from "mobx"
import * as oauth from "oauth4webapi"
import { Wretch } from "wretch"
import { getRetryMiddleware } from "#src/features/auth/authMiddleware.js"
import { AuthInfo } from "#src/features/auth/stores/AuthInfo.js"

/**
 * The client ID of the main JS app.
 */
const JS_CLIENT_ID = "oes"

/**
 * The redirect URI.
 */
const REDIRECT_URI = "/auth/redirect"

/**
 * The local storage key for the auth data.
 */
const LOCAL_STORAGE_KEY = "oes-auth-data-v1"

/**
 * Stores auth status/tokens.
 */
export class AuthStore {
  /**
   * A {@link Wretch} with auth middlewares added.
   */
  authWretch: Wretch

  private authInfo: AuthInfo | null = null
  private authInfoPromise: Promise<AuthInfo | null> = Promise.resolve(null)

  private client: oauth.Client
  private authServer: oauth.AuthorizationServer

  constructor(serverBaseURL: URL, public wretch: Wretch) {
    this.authWretch = wretch.middlewares([
      getRetryMiddleware(serverBaseURL, this),
    ])

    this.client = {
      client_id: JS_CLIENT_ID,
      token_endpoint_auth_method: "none",
    }

    let baseURLStr = serverBaseURL.toString()
    if (baseURLStr.endsWith("/")) {
      baseURLStr = baseURLStr.substring(0, baseURLStr.length - 1)
    }

    this.authServer = {
      issuer: JS_CLIENT_ID, // TODO
      token_endpoint: `${baseURLStr}/auth/token`,
    }

    makeAutoObservable<this, "client" | "authServer">(this, {
      wretch: false,
      authWretch: false,
      client: false,
      authServer: false,
    })

    // update the auth info if another window updates it in storage
    window.addEventListener("storage", (e) => {
      if (e.key == LOCAL_STORAGE_KEY && e.newValue) {
        try {
          const obj = JSON.parse(e.newValue)
          const loaded = AuthInfo.createFromObject(obj)
          if (loaded && !loaded.getIsExpired()) {
            this.setAuthInfo(loaded)
          }
        } catch (_) {
          // ignore
        }
      }
    })
  }

  /**
   * The current access token.
   */
  get accessToken(): string | null {
    return this.authInfo?.accessToken ?? null
  }

  /**
   * The current email.
   */
  get email(): string | null {
    return this.authInfo?.email ?? null
  }

  /**
   * The current access token scope.
   */
  get scope(): string[] | null {
    if (this.authInfo?.scope != null) {
      return this.authInfo.scope.split(" ")
    } else {
      return null
    }
  }

  /**
   * Get a promise that resolves to an {@link AuthInfo}.
   */
  async getAuthInfo(): Promise<AuthInfo> {
    let promise = this.authInfoPromise
    let authInfo = await promise
    while (!authInfo) {
      await when(() => this.authInfoPromise != promise)
      promise = this.authInfoPromise
      authInfo = await promise
    }

    return authInfo
  }

  /**
   * Set the current {@link AuthInfo}.
   */
  setAuthInfo(authInfo: AuthInfo | null): Promise<AuthInfo | null> {
    this.authInfoPromise = this.authInfoPromise.then(
      action(() => {
        this.authInfo = authInfo
        saveAuthInfo(authInfo)
        return authInfo
      })
    )
    return this.authInfoPromise
  }

  /**
   * Load a saved token from storage.
   * @returns The loaded token, or null if not found/not usable.
   */
  async load(): Promise<AuthInfo | null> {
    const loaded = loadAuthInfo()
    if (loaded) {
      if (loaded.getIsExpired()) {
        const refreshed = await this._refresh(loaded)
        if (refreshed) {
          await this.setAuthInfo(refreshed)
        }
        return refreshed
      } else {
        await this.setAuthInfo(loaded)
        return loaded
      }
    } else {
      return null
    }
  }

  /**
   * Attempt to refresh the given {@link AuthInfo}.
   */
  async attemptRefresh(authInfo: AuthInfo): Promise<AuthInfo | null> {
    this.authInfoPromise = this.authInfoPromise.then(async (curAuthInfo) => {
      // bail if the current auth info was changed
      if (curAuthInfo?.accessToken != authInfo.accessToken) {
        return curAuthInfo
      }

      const refreshed = await this._refresh(curAuthInfo)
      runInAction(() => {
        this.authInfo = refreshed
      })
      saveAuthInfo(refreshed)
      return refreshed
    })
    return this.authInfoPromise
  }

  /** OAuth refresh. */
  private async _refresh(authToken: AuthInfo): Promise<AuthInfo | null> {
    if (!authToken.refreshToken) {
      return null
    }

    const resp = await oauth.refreshTokenGrantRequest(
      this.authServer,
      this.client,
      authToken.refreshToken
    )

    const parsed = await oauth.processRefreshTokenResponse(
      this.authServer,
      this.client,
      resp
    )

    if (oauth.isOAuth2Error(parsed)) {
      return null
    }

    return AuthInfo.createFromResponse(parsed)
  }
}

/**
 * Save the {@link AuthInfo} to local storage.
 */
const saveAuthInfo = (info: AuthInfo | null) => {
  if (info) {
    const stringified = JSON.stringify(info)
    window.localStorage.setItem(LOCAL_STORAGE_KEY, stringified)
  } else {
    window.localStorage.removeItem(LOCAL_STORAGE_KEY)
  }
}

/**
 * Load the {@link AuthInfo} from local storage.
 */
const loadAuthInfo = (): AuthInfo | null => {
  const stringified = window.localStorage.getItem(LOCAL_STORAGE_KEY)
  if (stringified) {
    try {
      const obj = JSON.parse(stringified)
      return AuthInfo.createFromObject(obj)
    } catch (_) {
      return null
    }
  } else {
    return null
  }
}
