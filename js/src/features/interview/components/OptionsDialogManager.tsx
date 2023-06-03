import { fetchCartInterview } from "#src/features/cart/api.js"
import {
  fetchCurrentOrEmptyCart,
  getCurrentCartId,
} from "#src/features/cart/utils.js"
import { useInterviewState } from "#src/features/interview/hooks.js"
import { OptionsDialog } from "#src/features/selfservice/components/options/OptionsDialog.js"
import { InterviewOption } from "#src/features/selfservice/types.js"
import { useWretch } from "#src/hooks/api.js"
import { useNavigate } from "#src/hooks/location.js"
import { useLocation } from "#src/hooks/location.js"

declare module "#src/hooks/location.js" {
  interface LocationState {
    showAddOptionsDialog?: {
      eventId: string
      registrationId?: string
    }
  }
}

export type OptionsDialogManagerProps = {
  eventId: string
  registrationId?: string
  options: InterviewOption[]
}

export const OptionsDialogManager = (props: OptionsDialogManagerProps) => {
  const { eventId, registrationId, options } = props

  const wretch = useWretch()
  const loc = useLocation()
  const show =
    loc.state?.showAddOptionsDialog?.eventId == eventId &&
    loc.state.showAddOptionsDialog.registrationId == registrationId
  const navigate = useNavigate()
  const interviewState = useInterviewState()

  const startInterview = async (id: string) => {
    let currentCartId = getCurrentCartId()

    if (!currentCartId) {
      const [fetchedCartId] = await fetchCurrentOrEmptyCart(wretch, eventId)
      currentCartId = fetchedCartId
    }

    const state = await fetchCartInterview(
      wretch,
      currentCartId,
      id,
      registrationId
    )
    const next = await interviewState.startInterview(state, {
      cartId: currentCartId,
      eventId: eventId,
    })

    navigate(loc, {
      replace: true,
      state: {
        ...loc.state,
        showAddOptionsDialog: undefined,
        showInterviewDialog: {
          eventId: eventId,
          recordId: next.id,
        },
      },
    })
  }

  return (
    <OptionsDialog
      opened={show}
      options={options.map((o) => ({ id: o.id, label: o.name }))}
      onClose={() => {
        navigate(-1)
      }}
      onSelect={startInterview}
    />
  )
}
