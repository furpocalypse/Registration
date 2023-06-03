// eslint-disable-next-line @typescript-eslint/no-empty-interface
export interface PaymentServiceMap {
  // empty
}

export type PaymentServiceID = keyof PaymentServiceMap

export interface CheckoutMethod {
  service: string
  method?: string
  name?: string
}

export interface CheckoutExternalData {
  [key: string]: unknown
}

export interface CheckoutResponse<ID extends PaymentServiceID> {
  id: string
  service: ID
  external_id: string
  data: PaymentServiceMap[ID]
}
