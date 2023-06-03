import { AuthMethod, AuthToken } from "#src/features/auth/types/auth.js"
import { Wretch } from "wretch"

const toUint8Array = (s: string) => Uint8Array.from(s, (c) => c.charCodeAt(0))

export interface WebAuthnConfig {
  rpId: string
  rpName: string
  algorithms: { alg: number; type: "public-key" }[]
}

export interface WebAuthnUserInfo {
  id: string
  name: string
  displayName: string
}

export interface WebAuthnCreateOptions {
  challenge: string
  userInfo: WebAuthnUserInfo
}

export class WebAuthnAuth implements AuthMethod {
  id = "webauthn"

  constructor(public wretch: Wretch, public config: WebAuthnConfig) {}

  async checkAvailable(): Promise<boolean> {
    if (!("PublicKeyCredential" in window)) {
      return false
    }

    try {
      const platformAvailable =
        await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
      return platformAvailable
    } catch (err) {
      return false
    }
  }

  async createCredentials(options: WebAuthnCreateOptions) {
    const pubkeyOptions: PublicKeyCredentialCreationOptions = {
      challenge: toUint8Array(options.challenge),
      rp: {
        id: this.config.rpId,
        name: this.config.rpName,
      },
      user: {
        id: toUint8Array(options.userInfo.id),
        name: options.userInfo.name,
        displayName: options.userInfo.displayName,
      },
      pubKeyCredParams: this.config.algorithms,
      authenticatorSelection: {
        authenticatorAttachment: "platform",
      },
      attestation: "none",
      timeout: 60000,
    }

    return await navigator.credentials.create({
      publicKey: pubkeyOptions,
    })
  }

  checkRefreshable(): Promise<boolean> {
    throw new Error("Method not implemented.")
  }
  refresh(): Promise<AuthToken | null> {
    throw new Error("Method not implemented.")
  }
}
