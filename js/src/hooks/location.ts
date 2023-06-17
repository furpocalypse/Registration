import { useMemo } from "react"
import {
  Location,
  NavigateOptions,
  To,
  useLocation as originalUseLocation,
  useNavigate as originalUseNavigate,
} from "react-router-dom"

/**
 * Interface for the Location's `state` object.
 */
export interface LocationState {
  [key: string]: unknown | undefined
}

export type TypedLocation = Omit<Location, "state"> & { state?: LocationState }

/**
 * react-router's `useLocation` hook but with improved typing.
 */
export const useLocation = (): TypedLocation => {
  const loc = originalUseLocation()
  return loc
}

type TypedNavigateOptions = Omit<NavigateOptions, "state"> & {
  state?: LocationState
}

export interface TypedNavigateFunction {
  (to: To, options?: TypedNavigateOptions): void
  (delta: number): void
}

/**
 * react-router's `useNavigate` but with improved typing.
 */
export const useNavigate = (): TypedNavigateFunction => {
  const origNavigate = originalUseNavigate()

  return useMemo(() => {
    const navigate = (to: To | number, options?: TypedNavigateOptions) => {
      if (typeof to === "number") {
        return origNavigate(to)
      } else {
        return origNavigate(to, options)
      }
    }

    return navigate
  }, [origNavigate])
}
