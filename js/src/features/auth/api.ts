import {
  AccountInfo,
  EmailTokenResponse,
} from "#src/features/auth/types/AccountInfo.js"
import {
  WebAuthnChallenge,
  WebAuthnChallengeResult,
} from "#src/features/auth/types/WebAuthn.js"
import * as oauth from "oauth4webapi"
import { Wretch } from "wretch"

/**
 * Get the current account information.
 */
export const getAccountInfo = async (wretch: Wretch): Promise<AccountInfo> => {
  return await wretch.url("/auth/account").get().json<AccountInfo>()
}

/**
 * Send a verification code to the given email.
 */
export const sendVerificationEmail = async (
  wretch: Wretch,
  email: string
): Promise<void> => {
  return await wretch
    .url("/auth/email/send")
    .json({ email: email })
    .post()
    .res()
}

/**
 * Verify an email.
 */
export const verifyEmail = async (
  wretch: Wretch,
  email: string,
  code: string
): Promise<EmailTokenResponse | null> => {
  return await wretch
    .url("/auth/email/verify")
    .json({ email: email, code: code })
    .post()
    .forbidden(() => null)
    .json<EmailTokenResponse>()
}

/**
 * Create a new account without credentials.
 */
export const createAccount = async (
  wretch: Wretch,
  emailToken?: string | null
): Promise<oauth.TokenEndpointResponse> => {
  return await wretch
    .url("/auth/account/create")
    .json({
      email_token: emailToken ?? null,
    })
    .post()
    .json<oauth.TokenEndpointResponse>()
}

/**
 * Get WebAuthn a registration challenge and options.
 */
export const getWebAuthnRegistrationChallenge = async (
  wretch: Wretch
): Promise<WebAuthnChallenge> => {
  return await wretch
    .url("/auth/webauthn/register")
    .get()
    .json<WebAuthnChallenge>()
}

/**
 * Complete a WebAuthn registration.
 */
export const completeWebAuthnRegistration = async (
  wretch: Wretch,
  request: WebAuthnChallengeResult
): Promise<oauth.TokenEndpointResponse | null> => {
  return await wretch
    .url("/auth/webauthn/register")
    .json(request)
    .post()
    .badRequest(() => null)
    .json<oauth.TokenEndpointResponse>()
}

/**
 * Get a challenge to authenticate using the given credential ID.
 */
export const getWebAuthnAuthenticationChallenge = async (
  wretch: Wretch,
  credentialId: string
): Promise<WebAuthnChallenge> => {
  return await wretch
    .url(`/auth/webauthn/authenticate/${credentialId}`)
    .get()
    .json<WebAuthnChallenge>()
}

/**
 * Complete WebAuthn authentication.
 */
export const completeWebAuthnAuthentication = async (
  wretch: Wretch,
  request: WebAuthnChallengeResult
): Promise<oauth.TokenEndpointResponse | null> => {
  return await wretch
    .url("/auth/webauthn/authenticate")
    .json(request)
    .post()
    .forbidden(() => null)
    .json<oauth.TokenEndpointResponse>()
}
