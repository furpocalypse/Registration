import { useLocation, useNavigate } from "#src/hooks/location.js"
import {
  CompleteInterviewStateResponse,
  InterviewStateMetadata,
} from "@oes/interview-lib"
import { InterviewDialog } from "@oes/interview-components/components/interview/InterviewDialog.js"
import { observer } from "mobx-react-lite"
import { useInterviewState } from "#src/features/interview/hooks.js"

declare module "#src/hooks/location.js" {
  interface LocationState {
    showInterviewDialog?: {
      eventId: string
      recordId: string
    }
  }
}

export type InterviewDialogManagerProps = {
  eventId: string
  onComplete?: (
    response: CompleteInterviewStateResponse,
    metadata?: InterviewStateMetadata
  ) => Promise<void>
}

export const InterviewDialogManager = observer(
  (props: InterviewDialogManagerProps) => {
    const stateStore = useInterviewState()
    const navigate = useNavigate()
    const loc = useLocation()
    const { showInterviewDialog } = loc.state ?? {}

    const record = showInterviewDialog
      ? stateStore.getRecord(showInterviewDialog.recordId)
      : undefined

    const show =
      record != null &&
      showInterviewDialog != null &&
      props.eventId == showInterviewDialog.eventId

    return (
      <InterviewDialog
        opened={show}
        stateStore={stateStore}
        recordId={showInterviewDialog?.recordId as string}
        onClose={() => {
          navigate(-1)
        }}
        onSubmit={async (values, button) => {
          if (!record) {
            return
          }

          const next = await stateStore.updateInterview(
            record,
            values,
            button ?? undefined
          )

          // if complete, close dialog and call the handler
          // otherwise, save the new state and push onto the history stack
          if (next.stateResponse.complete) {
            navigate(loc, {
              state: { ...loc.state, showInterviewDialog: undefined },
            })

            props.onComplete &&
              props.onComplete(next.stateResponse, next.metadata)
          } else {
            stateStore.records.set(next.id, next)
            stateStore.save()

            navigate(loc, {
              state: {
                ...loc.state,
                showInterviewDialog: {
                  eventId: props.eventId,
                  recordId: next.id,
                },
              },
            })
          }
        }}
      />
    )
  }
)

InterviewDialogManager.displayName = "InterviewDialogManager"
