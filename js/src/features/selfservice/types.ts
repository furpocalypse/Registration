export interface SelfServiceRegistration {
  id: string
  title?: string
  subtitle?: string
  description?: string
}

export interface InterviewOption {
  id: string
  name: string
}

export interface SelfServiceRegistrationResponse {
  registration: SelfServiceRegistration
  change_options: InterviewOption[]
}

export interface SelfServiceRegistrationListResponse {
  registrations: SelfServiceRegistrationResponse[]
  add_options: InterviewOption[]
}

declare module "@oes/interview-lib" {
  interface InterviewStateMetadata {
    eventId?: string
    cartId?: string
  }
}
