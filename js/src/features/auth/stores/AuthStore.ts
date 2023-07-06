import { action, makeObservable, observable, runInAction } from "mobx"
import * as oauth from "oauth4webapi"
import * as yup from "yup"
import { Wretch } from "wretch"
import {
  getAccessTokenMiddleware,
  getRetryMiddleware,
} from "#src/features/auth/authMiddleware.js"

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

const authInfoSchema = yup.object({
  tokenType: yup.string().defined(),
  accessToken: yup.string().defined(),
  refreshToken: yup.string().nullable(),
  expiresAt: yup.number().nullable(),
  scope: yup.string().nullable(),
})

/**
 * Store auth information.
 */
export class AuthInfo {
  constructor(
    private _tokenType: string,
    private _accessToken: string,
    private _refreshToken: string | null = null,
    private _expiresAt: number | null = null,
    private _scope: string | null = null
  ) {}

  /**
   * The access token.
   */
  get accessToken(): string {
    return this._accessToken
  }

  /**
   * The refresh token.
   */
  get refreshToken(): string | null {
    return this._refreshToken
  }

  /**
   * The access token expiration date.
   */
  get expiresAt(): Date | null {
    if (this._expiresAt != null) {
      return new Date(this._expiresAt * 1000)
    } else {
      return null
    }
  }

  /**
   * The scope.
   */
  get scope(): string | null {
    return this._scope
  }

  /**
   * Create a {@link AuthInfo} from a token endpoint response.
   */
  static createFromResponse(response: oauth.TokenEndpointResponse): AuthInfo {
    let expiresAt = null
    if (response.expires_in != null) {
      const now = Math.floor(new Date().getTime() / 1000)
      expiresAt = now + response.expires_in
    }

    return new AuthInfo(
      response.token_type,
      response.access_token,
      response.refresh_token ?? null,
      expiresAt,
      response.scope ?? null
    )
  }

  /**
   * Parse a {@link AuthInfo} from an object.
   *
   * @returns A {@link AuthInfo} object, or null if it could not be parsed.
   */
  static createFromObject(obj: object): AuthInfo | null {
    try {
      const parsed = authInfoSchema.validateSync(obj)
      return new AuthInfo(
        parsed.tokenType,
        parsed.accessToken,
        parsed.refreshToken ?? null,
        parsed.expiresAt ?? null,
        parsed.scope ?? null
      )
    } catch (_) {
      return null
    }
  }

  /**
   * Return whether the access token is expired.
   */
  getIsExpired(): boolean {
    const now = Math.floor(new Date().getTime() / 1000)
    return this._expiresAt != undefined && now >= this._expiresAt
  }

  toJSON() {
    return {
      tokenType: this._tokenType,
      accessToken: this._accessToken,
      refreshToken: this._refreshToken,
      expiresAt: this._expiresAt,
      scope: this._scope,
    }
  }
}

export class AuthStore {
  private _authWretch: Wretch

  private client: oauth.Client
  private authServer: oauth.AuthorizationServer

  private authInfo: AuthInfo | null = null
  private _loaded = false
  private _invalid = false

  /**
   * A {@link Wretch} instance with authorization features added.
   */
  get authWretch(): Wretch {
    return this._authWretch
  }

  /**
   * Whether the auth status has been loaded.
   */
  get loaded(): boolean {
    return this._loaded
  }

  /**
   * The current access token.
   */
  get accessToken(): string | null {
    return this.authInfo?.accessToken ?? null
  }

  constructor(serverBaseURL: URL, public wretch: Wretch) {
    this._authWretch = wretch.middlewares([
      getRetryMiddleware(this),
      getAccessTokenMiddleware(serverBaseURL, this),
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

    makeObservable<this, "authInfo" | "_loaded" | "_invalid">(this, {
      authInfo: observable.ref,
      _loaded: observable,
      _invalid: observable,
      setup: action,
      setAuthInfo: action,
      markInvalid: action,
      refresh: action,
    })

    // update the auth info if another window updates it in storage
    window.addEventListener("storage", (e) => {
      if (e.key == LOCAL_STORAGE_KEY && e.newValue) {
        try {
          const obj = JSON.parse(e.newValue)
          const loaded = AuthInfo.createFromObject(obj)
          if (loaded) {
            runInAction(() => {
              this.authInfo = loaded
              this._invalid = false
            })
          }
        } catch (_) {
          // ignore
        }
      }
    })
  }

  /**
   * Get whether the client is authorized/has a valid access token.
   */
  getIsAuthorized(): boolean {
    return (
      this._loaded &&
      !!this.authInfo?.accessToken &&
      !this.authInfo.getIsExpired() &&
      !this._invalid
    )
  }

  /**
   * Set up the auth store.
   */
  async setup() {
    const loaded = loadAuthInfo()
    if (loaded) {
      if (!loaded.getIsExpired()) {
        this.authInfo = loaded
      } else if (loaded.refreshToken) {
        await this.refresh()
      }
    }

    runInAction(() => {
      this._loaded = true
    })
  }

  /**
   * Set the {@link AuthInfo}.
   */
  setAuthInfo(authInfo: AuthInfo | null) {
    this._invalid = false
    this.authInfo = authInfo
    saveAuthInfo(authInfo)
  }

  /**
   * Mark the given access token as being invalid.
   * @returns true if the state was updated, false if it was already marked invalid.
   */
  markInvalid(accessToken: string): boolean {
    if (this.authInfo?.accessToken == accessToken && !this._invalid) {
      this._invalid = true
      return true
    } else {
      return false
    }
  }

  /**
   * Attempt to use a refresh token.
   * @returns A new {@link AuthInfo} or null if unsuccessful.
   */
  async refresh(): Promise<AuthInfo | null> {
    if (!this.authInfo?.refreshToken) {
      this.setAuthInfo(null)
      return null
    }

    const resp = await oauth.refreshTokenGrantRequest(
      this.authServer,
      this.client,
      this.authInfo.refreshToken
    )

    const parsed = await oauth.processRefreshTokenResponse(
      this.authServer,
      this.client,
      resp
    )
    if (oauth.isOAuth2Error(parsed)) {
      this.setAuthInfo(null)
      return null
    }

    const newAuthInfo = AuthInfo.createFromResponse(parsed)
    this.setAuthInfo(newAuthInfo)
    return newAuthInfo
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
