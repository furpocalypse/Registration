import { AuthMethod, AuthToken } from "#src/features/auth/types/auth.js"
import { Wretch } from "wretch"

export class EmailAuth implements AuthMethod {
  id = "email"

  constructor(public wretch: Wretch) {}

  async checkAvailable(): Promise<boolean> {
    throw new Error("TODO: check config")
  }

  /**
   * Request a new login code to be sent to an email.
   * @param email - The email.
   * @returns true if the code was sent, false if not.
   */
  async requestCode(email: string): Promise<boolean> {
    throw new Error("TODO")
  }

  /**
   * Submit a code to receive a token.
   * @param email - The email.
   * @param code - The received code.
   * @returns The auth token, or null if the code wasn't valid.
   */
  async getToken(email: string, code: string): Promise<AuthToken | null> {
    throw new Error("TODO")
  }

  async checkRefreshable(): Promise<boolean> {
    // not refreshable
    return false
  }

  async refresh(): Promise<null> {
    // not refreshable
    return null
  }
}
