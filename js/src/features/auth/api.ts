import {
  WebAuthnChallenge,
  WebAuthnChallengeResult,
} from "#src/features/auth/types/WebAuthn.js"
import * as oauth from "oauth4webapi"
import { Wretch } from "wretch"

/**
 * Create a new account without credentials.
 */
export const createAccount = async (
  wretch: Wretch
): Promise<oauth.TokenEndpointResponse> => {
  return await wretch
    .url("/auth/account/create")
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
