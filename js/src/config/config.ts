import { Config } from "#src/types/config.js"

const configUrl = new URL("config.json", import.meta.url)

/**
 * Get the application configuration.
 */
export const fetchConfig = async (): Promise<Config> => {
  const result = await fetch(configUrl)
  if (!result.ok) {
    throw new Error("Could not load application configuration")
  }
  return await result.json()
}
