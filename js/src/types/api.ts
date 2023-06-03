import { Wretch } from "wretch"

export type APIFunc<T extends unknown[], R> = (
  wretch: Wretch,
  ...args: T
) => Promise<R>
