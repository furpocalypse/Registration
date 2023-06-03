export interface CartRegistration {
  id: string
  submission_id?: string
  old_data: Record<string, unknown>
  new_data: Record<string, unknown>
  meta?: Record<string, unknown>
}

// TODO: this will not always have data
export interface Cart {
  event_id: string
  registrations: CartRegistration[]
  meta?: Record<string, unknown>
}

export interface Modifier {
  name: string
  amount: number
}

export interface LineItem {
  registration_id: string
  name: string
  price: number
  total_price: number
  modifiers: Modifier[]
  description?: string
}

export interface PricingResult {
  currency: string
  line_items: LineItem[]
  total_price: number
  modifiers: Modifier[]
}
