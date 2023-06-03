import { placeholderWretch } from "#src/config/api.js"
import { InterviewStateStore } from "@oes/interview-lib"
import { createContext, useContext } from "react"

export const InterviewStateStoreContext = createContext(
  new InterviewStateStore(placeholderWretch)
)

export const useInterviewState = () => useContext(InterviewStateStoreContext)
