import { Loader, createLoader } from "#src/util/loader.js"
import { useState } from "react"

/**
 * Hook to create a {@link Loader} and keep it in component state.
 */
export const useLoader = <T>(
  loadFunc: () => Promise<T>,
  initialValue?: T
): Loader<T> => {
  const [loader] = useState(() => createLoader(loadFunc, initialValue))
  return loader
}
