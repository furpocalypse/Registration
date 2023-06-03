import { LoaderComponent } from "#src/components/loading/Loading.js"
import { makeAutoObservable, runInAction } from "mobx"
import { createElement, ComponentType, ReactNode } from "react"

export enum LoadingState {
  loading = "loading",
  ready = "ready",
  notFound = "notFound",
}

export interface LoaderComponentProps<T> {
  placeholder?: ReactNode
  notFound?: ReactNode
  children?: ((value: T) => ReactNode) | ReactNode
}

export interface Loader<T> extends Promise<T> {
  state: LoadingState
  value: T | null
  checkLoaded(): this is Loader<T> & { value: T }
  fetch(): Promise<T>
  load(): Promise<T>
  Component: ComponentType<LoaderComponentProps<T>>
}

/**
 * Thrown when a loading resource is not found.
 */
export class NotFoundError extends Error {
  constructor() {
    super()
  }
}

export type LoaderFactory<T> = (
  loadFunc: () => Promise<T>,
  initialValue?: T
) => Loader<T>

export const createLoader = <T>(
  loadFunc: () => Promise<T>,
  initialValue?: T
): Loader<T> => {
  const obj = makeAutoObservable({
    state: initialValue != null ? LoadingState.ready : LoadingState.loading,
    value: (initialValue ?? null) as T | null,
    loadingPromise: null as Promise<T> | null,
    checkLoaded() {
      return this.state == LoadingState.ready
    },
    async fetch() {
      try {
        const res = await loadFunc()
        runInAction(() => {
          this.value = res
          this.state = LoadingState.ready
        })
        return res
      } catch (e) {
        if (e instanceof NotFoundError) {
          runInAction(() => {
            this.state = LoadingState.notFound
          })
        }
        throw e
      }
    },
    async load() {
      if (!this.loadingPromise) {
        this.loadingPromise = this.fetch()
      }
      return await this.loadingPromise
    },
    Component: (props: Omit<LoaderComponentProps<T>, "loader">) => {
      return createElement(LoaderComponent<T>, { ...props, loader: obj })
    },
    then<R1 = T, R2 = never>(
      onfulfilled?: ((v: T) => R1 | PromiseLike<R1>) | null | undefined,
      onrejected?: ((error: unknown) => R2 | PromiseLike<R2>) | null | undefined
    ): Promise<R1 | R2> {
      return this.load().then(onfulfilled, onrejected)
    },
    catch<R2 = never>(
      onrejected?: ((error: unknown) => R2 | PromiseLike<R2>) | null | undefined
    ): Promise<T | R2> {
      return this.load().catch(onrejected)
    },
    finally(onfinally?: (() => void) | undefined | null): Promise<T> {
      return this.load().finally(onfinally)
    },
    [Symbol.toStringTag]: "[object Loader]",
  })

  return obj
}
