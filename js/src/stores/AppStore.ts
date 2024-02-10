import { Config } from "#src/types/config.js"
import { defaultWretch } from "#src/config/api.js"
import { makeAutoObservable } from "mobx"
import { Wretch } from "wretch"
import { fetchConfig } from "#src/config/config.js"
import { AuthStore } from "#src/features/auth/stores/AuthStore.js"

export class AppStore {
  authStore: AuthStore

  constructor(public wretch: Wretch, public config: Config) {
    const apiUrl = new URL(config.apiUrl, window.location.href)
    this.authStore = new AuthStore(apiUrl, wretch)

    makeAutoObservable(this, {
      config: false,
    })
  }

  static async fromConfig(): Promise<AppStore> {
    const config = await fetchConfig()
    const wretch = defaultWretch.url(config.apiUrl, true)
    return new AppStore(wretch, config)
  }
}
