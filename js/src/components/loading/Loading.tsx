import { Loader, LoadingState, NotFoundError } from "#src/util/loader.js"
import { observer } from "mobx-react-lite"
import { ReactNode, useEffect } from "react"

export type LoadingProps = {
  state: LoadingState
  placeholder?: ReactNode
  children?: ReactNode
  notFound?: ReactNode
}

export const Loading = ({
  state,
  placeholder,
  children,
  notFound,
}: LoadingProps) => {
  let content
  switch (state) {
    case LoadingState.loading:
      content = placeholder
      break
    case LoadingState.notFound:
      content = notFound ?? placeholder
      break
    case LoadingState.ready:
      content = children
      break
  }

  return <>{content}</>
}

export type LoaderComponentProps<T> = {
  loader: Loader<T>
  children?: ((value: T) => ReactNode) | ReactNode
  placeholder?: ReactNode
  notFound?: ReactNode
}

export const LoaderComponent = observer(
  <T,>({
    loader,
    children,
    placeholder,
    notFound,
  }: LoaderComponentProps<T>) => {
    useEffect(() => {
      loader.load().catch((err) => {
        if (err instanceof NotFoundError) {
          // ignore
        } else {
          throw err
        }
      })
    }, [loader])

    let childContent
    if (loader.checkLoaded()) {
      const value = loader.value
      if (typeof children == "function") {
        childContent = children(value)
      } else {
        childContent = children
      }
    }

    return (
      <Loading
        state={loader.state}
        placeholder={placeholder}
        notFound={notFound}
      >
        {childContent}
      </Loading>
    )
  }
)

LoaderComponent.displayName = "LoaderComponent"
