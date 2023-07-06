import {
  completeWebAuthnAuthentication,
  completeWebAuthnRegistration,
  createAccount,
  getWebAuthnAuthenticationChallenge,
  getWebAuthnRegistrationChallenge,
} from "#src/features/auth/api.js"
import { AuthInfo, AuthStore } from "#src/features/auth/stores/AuthStore.js"
import {
  browserSupportsWebAuthn,
  platformAuthenticatorIsAvailable,
  startAuthentication,
  startRegistration,
} from "@simplewebauthn/browser"
import { Wretch } from "wretch"

/**
 * The local storage key for the stored credential ID.
 */
const WEBAUTHN_CREDENTIAL_ID_LOCAL_STORAGE_KEY = "oes-credential-id-v1"

/**
 * Manage account creation/login.
 */
export class AccountStore {
  constructor(private wretch: Wretch, private authStore: AuthStore) {}

  /**
   * Create a new account and update the {@link AuthStore}.
   */
  async createNewAccount() {
    const tokenResponse = await createAccount(this.wretch)
    const authInfo = AuthInfo.createFromResponse(tokenResponse)
    this.authStore.setAuthInfo(authInfo)
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
   * @returns whether creation was successful.
   */
  async createWebAuthnAccount(): Promise<boolean> {
    const challenge = await getWebAuthnRegistrationChallenge(this.wretch)

    let attestationResponse
    try {
      attestationResponse = await startRegistration(challenge.options)
    } catch (err) {
      console.error("WebAuthn registration failed:", err)
      return false
    }

    const credentialId = attestationResponse.id

    const tokenResponse = await completeWebAuthnRegistration(this.wretch, {
      challenge: challenge.challenge,
      result: JSON.stringify(attestationResponse),
    })

    if (!tokenResponse) {
      return false
    }

    const authInfo = AuthInfo.createFromResponse(tokenResponse)

    window.localStorage.setItem(
      WEBAUTHN_CREDENTIAL_ID_LOCAL_STORAGE_KEY,
      credentialId
    )
    this.authStore.setAuthInfo(authInfo)
    return true
  }

  /**
   * Perform WebAuthn authentication.
   * @returns whether authentication was successful.
   */
  async performWebAuthnAuthentication() {
    const credentialId = this.getSavedWebAuthnCredentialId()
    if (!credentialId) {
      return false
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
      return false
    }

    const tokenResponse = await completeWebAuthnAuthentication(this.wretch, {
      challenge: challenge.challenge,
      result: JSON.stringify(authResult),
    })

    if (!tokenResponse) {
      return false
    }

    const authInfo = AuthInfo.createFromResponse(tokenResponse)
    this.authStore.setAuthInfo(authInfo)
    return true
  }
}
