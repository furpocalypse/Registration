import { createContext, useContext } from "react"

const format = (currency: string, amount: number) => {
  try {
    const formatter = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,

      // TODO: get these from a currency code DB
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })

    return formatter.format(amount / 100)
  } catch (e) {
    return null
  }
}

export type CurrencyProps = {
  amount: number
}

/**
 * Displays a formatted currency.
 */
export const Currency = (props: CurrencyProps) => {
  const { amount } = props
  const currencyCode = useContext(CurrencyContext)

  // TODO: currency formatting
  return <>{format(currencyCode, amount)}</>
}

export const CurrencyContext = createContext("USD")
