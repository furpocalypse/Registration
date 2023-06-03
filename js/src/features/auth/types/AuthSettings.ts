import { AuthorizationData } from "#src/features/auth/types/AuthData.js"

export interface AuthSettings {
  authorizationData?: AuthorizationData
  webAuthnCredentialId?: string
}
