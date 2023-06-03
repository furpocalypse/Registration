import * as yup from "yup"

export interface AuthStatusResponse {
  id: string
  scope: string
  email?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in?: number
  refresh_token?: string
  scope?: string
}

const schema = yup.object({
  accessToken: yup.string().required(),
  tokenType: yup.string().required(),
  expiresAt: yup.number(),
  refreshToken: yup.string(),
  scope: yup.string(),
})

/**
 * Stores an access token, expiration info, and refresh token.
 */
export class AuthorizationData {
  constructor(
    public accessToken: string,
    public tokenType: string,
    public expiresAt: Date | null,
    public refreshToken: string | null,
    public scope: string | null
  ) {}

  /**
   * Create an instance from a {@link TokenResponse}.
   */
  static createFromTokenResponse(response: TokenResponse): AuthorizationData {
    let expires_at: Date | null = null
    if (response.expires_in != null) {
      const now = new Date().getTime()
      expires_at = new Date(now + response.expires_in * 1000)
    }

    return new this(
      response.access_token,
      response.token_type,
      expires_at,
      response.refresh_token ?? null,
      response.scope ?? null
    )
  }

  /**
   * Create from a JSON object.
   * @param data - The JSON object.
   * @returns The {@link AuthorizationData}, or `null` if invalid.
   */
  static createFromJSON(data: unknown): AuthorizationData | null {
    try {
      const parsed = schema.validateSync(data)
      return new this(
        parsed.accessToken,
        parsed.tokenType,
        parsed.expiresAt != null ? new Date(parsed.expiresAt) : null,
        parsed.refreshToken ?? null,
        parsed.scope ?? null
      )
    } catch (_) {
      return null
    }
  }

  /**
   * The scopes as an array of strings.
   */
  get scopes(): string[] {
    return this.scope != null ? this.scope.split(" ") : []
  }

  /**
   * Check whether this token is valid.
   * @param now - The current {@link Date}.
   * @returns Whether the token is valid.
   */
  checkValid(now?: Date): boolean {
    if (this.expiresAt == null) {
      return true // unknown expiration date, assume valid and see if it fails
    }

    now = now == undefined ? new Date() : now
    const nowT = now.getTime()
    const expiresT = this.expiresAt.getTime()
    return nowT < expiresT
  }

  toJSON() {
    return {
      accessToken: this.accessToken,
      tokenType: this.tokenType,
      expiresAt: this.expiresAt?.getTime(),
      refreshToken: this.refreshToken ?? undefined,
      scope: this.scope ?? undefined,
    }
  }
}
