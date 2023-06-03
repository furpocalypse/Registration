import {
  AuthStatusResponse,
  TokenResponse,
} from "#src/features/auth/types/AuthData.js"
import {
  CreateWebAuthnRegistrationRequest,
  WebAuthChallenge,
  WebAuthnAuthenticationRequest,
} from "#src/features/auth/types/WebAuthn.js"
import { Wretch } from "wretch"
import { formUrlAddon, queryStringAddon } from "wretch/addons"

/**
 * Check the status of the given access token.
 * @param wretch - The {@link Wretch} instance, which should not have any auth settings
 *   configured.
 * @param accessToken - The access token to check.
 * @returns A {@link AuthStatusResponse} or `null` if not valid.
 */
export const checkAuthStatus = async (
  wretch: Wretch,
  accessToken: string
): Promise<AuthStatusResponse | null> => {
  const res = await wretch
    .url("/auth/current")
    .headers({
      Authorization: `Bearer ${accessToken}`,
    })
    .get()
    .unauthorized(() => {
      return null
    })
    .forbidden(() => {
      return null
    })
    .json<AuthStatusResponse>()

  return res
}

/**
 * Use a refresh token for a new access token.
 * @param wretch - The {@link Wretch} instance, which should not have any auth settings.
 * @param refreshToken - The refresh token.
 * @returns The new token response, or `null` if the refresh failed.
 */
export const refreshAccessToken = async (
  wretch: Wretch,
  refreshToken: string
): Promise<TokenResponse | null> => {
  return await wretch
    .addon(formUrlAddon)
    .formUrl({
      grant_type: "refresh_token",
      refresh_token: refreshToken,
    })
    .url("/auth/token")
    .post()
    .unauthorized(() => null)
    .json<TokenResponse | null>()
}

/**
 * Create a new account.
 */
export const createAccount = async (wretch: Wretch): Promise<TokenResponse> => {
  return await wretch.url("/auth/new-account").post().json<TokenResponse>()
}

/**
 * Get WebAuthn a registration challenge and options.
 */
export const getWebAuthnRegistrationChallenge = async (
  wretch: Wretch
): Promise<WebAuthChallenge> => {
  return await wretch
    .url("/auth/webauthn/register")
    .get()
    .json<WebAuthChallenge>()
}

/**
 * Create a WebAuthn registration.
 */
export const createWebAuthnRegistration = async (
  wretch: Wretch,
  request: CreateWebAuthnRegistrationRequest
): Promise<TokenResponse> => {
  return await wretch
    .url("/auth/webauthn/register")
    .json(request)
    .post()
    .json<TokenResponse>()
}

/**
 * Get a challenge to authenticate as a given account ID.
 */
export const getWebAuthnAuthenticationChallenge = async (
  wretch: Wretch,
  credentialId: string
): Promise<WebAuthChallenge> => {
  return await wretch
    .url("/auth/webauthn")
    .addon(queryStringAddon)
    .query({ credential_id: credentialId })
    .get()
    .json<WebAuthChallenge>()
}

/**
 * Complete WebAuthn authentication.
 */
export const completeWebAuthnAuthentication = async (
  wretch: Wretch,
  request: WebAuthnAuthenticationRequest
): Promise<TokenResponse> => {
  return await wretch
    .url("/auth/webauthn")
    .json(request)
    .post()
    .json<TokenResponse>()
}
