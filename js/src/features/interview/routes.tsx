import { InterviewStateStoreContext } from "#src/features/interview/hooks.js"
import { useWretch } from "#src/hooks/api.js"
import { InterviewStateStore } from "@oes/interview-lib"
import { ReactNode, useEffect, useState } from "react"

export const InterviewStateStoreProvider = ({
  children,
}: {
  children?: ReactNode
}) => {
  const wretch = useWretch()
  const [store] = useState(() => new InterviewStateStore(wretch))

  useEffect(() => {
    store.load()
  }, [store])

  return (
    <InterviewStateStoreContext.Provider value={store}>
      {children}
    </InterviewStateStoreContext.Provider>
  )
}
