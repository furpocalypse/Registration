export interface WebAuthChallenge {
  challenge: string
  options: Record<string, unknown>
}

export interface CreateWebAuthnRegistrationRequest {
  challenge: string
  result: string
}

export interface WebAuthnAuthenticationRequest {
  challenge: string
  result: string
}
