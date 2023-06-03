import { action, autorun, makeAutoObservable, runInAction } from "mobx"
import { observer } from "mobx-react-lite"
import { ReactNode, createContext, useContext, useEffect } from "react"

class TitleState {
  title: string[] = []
  subtitle: string[] = []

  constructor() {
    makeAutoObservable(this)

    autorun(() => {
      if (this.title.length > 0) {
        const title = this.title[this.title.length - 1]
        document.title = title
      }
    })
  }
}

export const TitlePlaceholder = observer(() => {
  const state = useContext(TitleContext)

  let title
  if (state.title.length > 0) {
    title = state.title[state.title.length - 1]
  }

  return <>{title}</>
})

export const SubtitlePlaceholder = observer(() => {
  const state = useContext(TitleContext)

  let subtitle
  if (state.subtitle.length > 0) {
    subtitle = state.subtitle[state.subtitle.length - 1]
  }

  return <>{subtitle}</>
})

export const Title = ({
  children,
  title,
}: {
  children?: ReactNode
  title: string
}) => {
  const state = useContext(TitleContext)

  useEffect(() => {
    runInAction(() => {
      state.title.push(title)
    })

    return action(() => {
      state.title.pop()
    })
  }, [])

  return <>{children}</>
}

export const Subtitle = ({
  children,
  subtitle,
}: {
  children?: ReactNode
  subtitle: string
}) => {
  const state = useContext(TitleContext)

  useEffect(() => {
    runInAction(() => {
      state.subtitle.push(subtitle)
    })

    return action(() => {
      state.subtitle.pop()
    })
  }, [])

  return <>{children}</>
}

export const TitleContext = createContext(new TitleState())
