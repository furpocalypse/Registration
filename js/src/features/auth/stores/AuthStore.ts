import {
  checkAuthStatus,
  completeWebAuthnAuthentication,
  createAccount,
  createWebAuthnRegistration,
  getWebAuthnAuthenticationChallenge,
  getWebAuthnRegistrationChallenge,
  refreshAccessToken,
} from "#src/features/auth/api.js"
import {
  AuthStatusResponse,
  AuthorizationData,
} from "#src/features/auth/types/AuthData.js"
import { AuthSettings } from "#src/features/auth/types/AuthSettings.js"
import {
  browserSupportsWebAuthn,
  platformAuthenticatorIsAvailable,
  startAuthentication,
  startRegistration,
} from "@simplewebauthn/browser"
import { makeAutoObservable, runInAction, when } from "mobx"
import {
  ConfiguredMiddleware,
  FetchLike,
  Wretch,
  WretchOptions,
  WretchResponse,
} from "wretch"

const LOCAL_STORAGE_KEY = "oes-auth-data"

/**
 * Store that holds authorization state.
 */
export class AuthStore {
  private _authorizationData: AuthorizationData | null = null
  private tokenReturnedUnauthorized = false
  private refreshPromise: Promise<AuthorizationData | null> | null = null
  private webAuthnCredentialId: string | null = null
  private _authWretch: Wretch
  private _setupComplete = false

  constructor(public wretch: Wretch, public authOrigin: string) {
    this._authWretch = wretch.middlewares([this.getAuthMiddleware()])
    makeAutoObservable(this)

    window.addEventListener("storage", (event) => {
      if (event.key == LOCAL_STORAGE_KEY && event.newValue) {
        const data = JSON.parse(event.newValue)
        if (data.authorizationData && data.authorizationData.accessToken) {
          // load new auth data if another window sets it
          runInAction(() => {
            this._authorizationData = AuthorizationData.createFromJSON(
              data.authorizationData
            )
            this.tokenReturnedUnauthorized = false
          })
        }
      }
    })
  }

  /**
   * Save the current settings to local storage.
   */
  save() {
    AuthStore.save({
      authorizationData: this._authorizationData ?? undefined,
      webAuthnCredentialId: this.webAuthnCredentialId ?? undefined,
    })
  }

  /**
   * Save {@link AuthSettings} to local storage.
   */
  static save(settings: AuthSettings) {
    const asStr = JSON.stringify(settings)
    window.localStorage.setItem(LOCAL_STORAGE_KEY, asStr)
  }

  /**
   * Load {@link AuthSettings} from local storage.
   */
  static load(): AuthSettings {
    try {
      const dataStr = window.localStorage.getItem(LOCAL_STORAGE_KEY)
      if (!dataStr) {
        return {}
      }

      const obj = JSON.parse(dataStr)
      const authData = AuthorizationData.createFromJSON(obj.authorizationData)
      return {
        authorizationData: authData ?? undefined,
        webAuthnCredentialId: obj.webAuthnCredentialId ?? undefined,
      }
    } catch (_) {
      return {}
    }
  }

  get setupComplete(): boolean {
    return this._setupComplete
  }

  get authorizationData(): AuthorizationData | null {
    return this._authorizationData
  }

  /**
   * Check whether the current {@link AuthorizationData} is valid.
   * @param now - The current time.
   */
  checkValid(now?: Date): boolean {
    return (
      this._authorizationData != null &&
      !this.tokenReturnedUnauthorized &&
      this._authorizationData.checkValid(now)
    )
  }

  /**
   * Whether a refresh token is present.
   */
  get canRefresh(): boolean {
    return !!this._authorizationData?.refreshToken
  }

  /**
   * A {@link Wretch} instance with authorization info included.
   */
  get authWretch(): Wretch {
    return this._authWretch
  }

  /**
   * Check the current auth status.
   */
  async getCurrentAuthStatus(): Promise<AuthStatusResponse | null> {
    if (!this._authorizationData) {
      return null
    }
    const token = this._authorizationData.accessToken
    const res = await checkAuthStatus(this.wretch, token)
    runInAction(() => {
      if (!res && token == this._authorizationData?.accessToken) {
        this.tokenReturnedUnauthorized = true
      }
    })
    return res
  }

  /**
   * Attempt to refresh the access token.
   *
   * Sets or clears the loaded {@link AuthorizationData} and updates local storage.
   *
   * @returns The new {@link AuthorizationData} or `null` if it fails.
   */
  async refresh(): Promise<AuthorizationData | null> {
    const refreshToken = this._authorizationData?.refreshToken as string
    const result = await refreshAccessToken(this.wretch, refreshToken)
    if (!result) {
      runInAction(() => {
        this._authorizationData = null
      })
      this.save()
      return null
    }

    return runInAction(() => {
      const authData = AuthorizationData.createFromTokenResponse(result)
      this._authorizationData = authData
      this.tokenReturnedUnauthorized = false
      this.save()
      return authData
    })
  }

  private async waitForValidToken(): Promise<string> {
    for (;;) {
      await when(() => this.checkValid())
      const token = this._authorizationData?.accessToken
      if (token) {
        return token
      }
    }
  }

  private getAuthMiddleware(): ConfiguredMiddleware {
    return (next) => async (url, opts) => {
      // continue as normal if the origin is unrelated
      const urlObj = new URL(url)
      if (urlObj.origin != this.authOrigin) {
        return await next(url, opts)
      }

      // retry on auth errors
      for (;;) {
        const accessToken = await this.waitForValidToken()
        const response = await fetchWithAuth(accessToken, next, url, opts)
        if (response.status != 401) {
          return response
        } else {
          // handle unauthorized

          // mark that the token returned unauthorized, unless something else changed it
          // in the meantime
          const currentToken = this._authorizationData?.accessToken
          runInAction(() => {
            if (currentToken == accessToken) {
              this.tokenReturnedUnauthorized = true
            }
          })

          // start a refresh attempt if it is possible and it has not already been
          // started
          if (
            currentToken == accessToken &&
            !this.refreshPromise &&
            this.canRefresh
          ) {
            // start the refresh process
            const refreshPromise = this.refresh()
              .catch(() => null)
              .then((res) => {
                runInAction(() => {
                  this.refreshPromise = null
                })
                return res
              })

            runInAction(() => {
              this.refreshPromise = refreshPromise
            })
          }

          // continue
        }
      }
    }
  }

  /**
   * Run initial setup.
   */
  async setup() {
    const curAuthSettings = AuthStore.load()
    if (curAuthSettings) {
      this._authorizationData = curAuthSettings.authorizationData ?? null
      this.webAuthnCredentialId = curAuthSettings.webAuthnCredentialId ?? null
    }

    if (!this.checkValid() && this.canRefresh) {
      await this.refresh()
    }

    if (!this.checkValid()) {
      // refresh didn't work, try webauthn signin
      if (this.webAuthnCredentialId) {
        try {
          const res = await this.performWebAuthnAuthorization(
            this.webAuthnCredentialId
          )
          runInAction(() => {
            this._authorizationData = res
            this.tokenReturnedUnauthorized = false
          })
          this.save()
        } catch (err) {
          console.error("WebAuthn authentication failed", err)
        }
      }
    }

    runInAction(() => {
      this._setupComplete = true
    })
  }

  /**
   * Create a new account.
   */
  async createAccount() {
    const newAccount = await createAccount(this.wretch)
    runInAction(() => {
      this._authorizationData =
        AuthorizationData.createFromTokenResponse(newAccount)
      this.tokenReturnedUnauthorized = false
      this.webAuthnCredentialId = null
    })
    this.save()
  }

  /**
   * Check if WebAuthn appears to be available.
   * @returns
   */
  checkWebAuthnAvailable(): boolean {
    return browserSupportsWebAuthn()
  }

  /**
   * Check if a user-verifying platform authenticator is available.
   */
  async checkPlatformAuthAvailable(): Promise<boolean> {
    return await platformAuthenticatorIsAvailable()
  }

  /**
   * Create a WebAuthn registration.
   */
  private async createWebAuthnRegistration(
    currentAccessToken: string
  ): Promise<[string, AuthorizationData] | null> {
    const wretch = this.wretch.headers({
      Authorization: `Bearer ${currentAccessToken}`,
    })

    const challenge = await getWebAuthnRegistrationChallenge(wretch)

    let attestationResponse
    try {
      attestationResponse = await startRegistration(challenge.options)
    } catch (err) {
      // ignore
      console.error("WebAuthn registration failed", err)
      return null
    }

    const credentialId = attestationResponse.id

    const tokenResponse = await createWebAuthnRegistration(wretch, {
      challenge: challenge.challenge,
      result: JSON.stringify(attestationResponse),
    })

    return [
      credentialId,
      AuthorizationData.createFromTokenResponse(tokenResponse),
    ]
  }

  /**
   * Create a new account via WebAuthn.
   * @returns
   */
  async createWebAuthnAccount() {
    const newAccount = await createAccount(this.wretch)
    try {
      const authResult = await this.createWebAuthnRegistration(
        newAccount.access_token
      )

      if (authResult) {
        const [credentialId, authData] = authResult

        runInAction(() => {
          this._authorizationData = authData
          this.tokenReturnedUnauthorized = false
          this.webAuthnCredentialId = credentialId
        })

        this.save()
        return
      }
    } catch (_) {
      // ignore
    }

    // set the original token
    runInAction(() => {
      this._authorizationData =
        AuthorizationData.createFromTokenResponse(newAccount)
      this.tokenReturnedUnauthorized = false
    })
    this.save()
  }

  private async performWebAuthnAuthorization(accountId: string) {
    const challenge = await getWebAuthnAuthenticationChallenge(
      this.wretch,
      accountId
    )
    const authResult = await startAuthentication(challenge.options)
    const tokenResponse = await completeWebAuthnAuthentication(this.wretch, {
      challenge: challenge.challenge,
      result: JSON.stringify(authResult),
    })

    return AuthorizationData.createFromTokenResponse(tokenResponse)
  }
}

/**
 * Call the fetch function with a given access token.
 * @param accessToken - The access token.
 */
const fetchWithAuth = async (
  accessToken: string,
  fetchLike: FetchLike,
  url: string,
  opts: WretchOptions
): Promise<WretchResponse> => {
  const newHeaders = new Headers(opts.headers)
  newHeaders.set("Authorization", `Bearer ${accessToken}`)

  return await fetchLike(url, { ...opts, headers: newHeaders })
}
