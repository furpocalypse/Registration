export interface WebAuthnChallenge {
  challenge: string
  options: Record<string, unknown>
}

export interface WebAuthnChallengeResult {
  challenge: string
  result: string
  email_token?: string | null
}
