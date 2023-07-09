import {
  completeWebAuthnAuthentication,
  completeWebAuthnRegistration,
  createAccount,
  getWebAuthnAuthenticationChallenge,
  getWebAuthnRegistrationChallenge,
  sendVerificationEmail,
  verifyEmail,
} from "#src/features/auth/api.js"
import { AuthStore } from "#src/features/auth/stores/AuthStore.js"
import { AuthInfo } from "#src/features/auth/stores/AuthInfo.js"
import {
  browserSupportsWebAuthn,
  platformAuthenticatorIsAvailable,
  startAuthentication,
  startRegistration,
} from "@simplewebauthn/browser"
import { Wretch } from "wretch"
import { action, makeAutoObservable, runInAction } from "mobx"

/**
 * The local storage key for the stored credential ID.
 */
const WEBAUTHN_CREDENTIAL_ID_LOCAL_STORAGE_KEY = "oes-credential-id-v1"

/**
 * Number of times WebAuthn will be tried.
 */
const WEBAUTHN_MAX_FAIL_COUNT = 2

/**
 * Options for account creation.
 */
export interface CreateAccountOptions {
  /**
   * Whether to allow a security key (non-platform authenticator) for WebAuthn.
   */
  allowSecurityKey?: boolean

  /**
   * A verified email token.
   */
  emailToken?: string
}

/**
 * Manage account creation/login.
 */
export class AccountStore {
  /**
   * Whether the initial auth setup finished.
   */
  public initialSetupComplete = false

  /**
   * Whether the initial auth finished.
   */
  public initialAuthComplete = false

  private webAuthnFailCount = 0

  constructor(private wretch: Wretch, private authStore: AuthStore) {
    makeAutoObservable(this)

    // set initial auth to complete when auth info becomes available
    authStore.getAuthInfo().then(
      action(() => {
        this.initialAuthComplete = true
      })
    )
  }

  /**
   * Perform initial setup.
   */
  async setup(): Promise<AuthInfo | null> {
    const loaded = await this.authStore.load()

    if (loaded) {
      runInAction(() => {
        this.initialSetupComplete = true
      })
      return loaded
    }

    // try to authenticate using other means
    let result = await this.authenticate()

    // kind of a hacky way to retry webauthn
    while (result === false) {
      await new Promise((r) => window.setTimeout(r, 1000))
      result = await this.authenticate()
    }

    runInAction(() => {
      this.initialSetupComplete = true
      this.webAuthnFailCount = 0
    })

    return result
  }

  /**
   * Send a verification email.
   */
  async sendVerificationEmail(email: string) {
    await sendVerificationEmail(this.wretch, email)
  }

  /**
   * Verify an email address.
   * @returns A validated email token, or null if not successful.
   */
  async verifyEmail(email: string, code: string): Promise<string | null> {
    const res = await verifyEmail(this.wretch, email, code)
    return res?.token ?? null
  }

  /**
   * Create a new account without credentials and update the {@link AuthStore}.
   */
  async createBasicAccount(emailToken?: string | null): Promise<AuthInfo> {
    const tokenResponse = await createAccount(this.wretch, emailToken)
    const authInfo = AuthInfo.createFromResponse(tokenResponse)
    await this.authStore.setAuthInfo(authInfo)
    return authInfo
  }

  /**
   * Check if WebAuthn appears to be available.
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
   * Get the saved WebAuthn credential ID
   */
  getSavedWebAuthnCredentialId(): string | null {
    const id = window.localStorage.getItem(
      WEBAUTHN_CREDENTIAL_ID_LOCAL_STORAGE_KEY
    )
    if (!id || typeof id !== "string") {
      return null
    } else {
      return id
    }
  }

  /**
   * Create an account using WebAuthn and update the {@link AuthStore}.
   * @returns The created account {@link AuthInfo} or null if unsuccessful.
   */
  async createWebAuthnAccount(
    emailToken?: string | null
  ): Promise<AuthInfo | null> {
    const challenge = await getWebAuthnRegistrationChallenge(this.wretch)

    let attestationResponse
    try {
      attestationResponse = await startRegistration(challenge.options)
    } catch (err) {
      console.error("WebAuthn registration failed:", err)
      return null
    }

    const credentialId = attestationResponse.id

    const tokenResponse = await completeWebAuthnRegistration(this.wretch, {
      challenge: challenge.challenge,
      result: JSON.stringify(attestationResponse),
      email_token: emailToken,
    })

    if (!tokenResponse) {
      return null
    }

    const authInfo = AuthInfo.createFromResponse(tokenResponse)

    window.localStorage.setItem(
      WEBAUTHN_CREDENTIAL_ID_LOCAL_STORAGE_KEY,
      credentialId
    )
    await this.authStore.setAuthInfo(authInfo)
    return authInfo
  }

  /**
   * Perform WebAuthn authentication.
   * @returns The resulting {@link AuthInfo} or null if unsuccessful.
   */
  async performWebAuthnAuthentication(): Promise<AuthInfo | null> {
    const credentialId = this.getSavedWebAuthnCredentialId()
    if (!credentialId) {
      return null
    }

    const challenge = await getWebAuthnAuthenticationChallenge(
      this.wretch,
      credentialId
    )

    let authResult
    try {
      authResult = await startAuthentication(challenge.options)
    } catch (err) {
      console.error("WebAuthn authentication failed:", err)
      return null
    }

    const tokenResponse = await completeWebAuthnAuthentication(this.wretch, {
      challenge: challenge.challenge,
      result: JSON.stringify(authResult),
    })

    if (!tokenResponse) {
      return null
    }

    const authInfo = AuthInfo.createFromResponse(tokenResponse)
    await this.authStore.setAuthInfo(authInfo)
    return authInfo
  }

  /**
   * Create an account.
   *
   * Tries to set up WebAuthn first, then falls back to a refresh-token-only account.
   *
   * @returns The resulting {@link AuthInfo}, null if unsuccessful, or false if an error
   *     occurred.
   */
  async createAccount(
    options?: CreateAccountOptions
  ): Promise<AuthInfo | false | null> {
    const hasWebAuthn = this.checkWebAuthnAvailable()
    const hasPlatformAuth = hasWebAuthn
      ? await this.checkPlatformAuthAvailable()
      : false
    const useWebAuthn =
      hasWebAuthn &&
      (hasPlatformAuth || !!options?.allowSecurityKey) &&
      this.webAuthnFailCount < WEBAUTHN_MAX_FAIL_COUNT

    if (useWebAuthn) {
      // retry loop
      const result = await this.createWebAuthnAccount(options?.emailToken)
      if (!result) {
        runInAction(() => {
          this.webAuthnFailCount++
        })
        return false
      } else {
        return result
      }
    }

    // fall back to standard account
    return await this.createBasicAccount(options?.emailToken)
  }

  /**
   * Attempt to authenticate.
   * @returns The {@link AuthInfo}, null if authentication was not possible, or false if
   *     there was an error.
   */
  async authenticate(): Promise<AuthInfo | false | null> {
    const hasWebAuthn = this.checkWebAuthnAvailable()
    const webAuthnCredentialId = this.getSavedWebAuthnCredentialId()

    const useWebAuthn =
      hasWebAuthn &&
      !!webAuthnCredentialId &&
      this.webAuthnFailCount < WEBAUTHN_MAX_FAIL_COUNT

    if (useWebAuthn) {
      const result = await this.performWebAuthnAuthentication()
      if (!result) {
        runInAction(() => {
          this.webAuthnFailCount++
        })
        if (this.webAuthnFailCount >= WEBAUTHN_MAX_FAIL_COUNT) {
          window.localStorage.removeItem(
            WEBAUTHN_CREDENTIAL_ID_LOCAL_STORAGE_KEY
          )
        }
        return false
      } else {
        return result
      }
    }

    return null
  }
}
