import { Title as PageTitle, Subtitle } from "#src/components/title/Title.js"
import { useParams } from "react-router-dom"
import { CardGrid } from "#src/features/selfservice/components/card/CardGrid.js"
import { Anchor, Box, Button, Grid } from "@mantine/core"
import { IconPlus } from "@tabler/icons-react"
import {
  RegistrationCard,
  RegistrationCardPlaceholder,
} from "#src/features/selfservice/components/card/RegistrationCard.js"
import { observer } from "mobx-react-lite"
import { useLocation, useNavigate } from "#src/hooks/location.js"
import { InterviewDialogManager } from "#src/features/interview/components/InterviewDialogManager.js"
import { OptionsDialogManager } from "#src/features/interview/components/OptionsDialogManager.js"
import { useSelfServiceLoader } from "#src/features/selfservice/hooks.js"
import { Event } from "#src/features/event/types.js"
import { SelfServiceRegistrationResponse } from "#src/features/selfservice/types.js"
import { fetchCartInterview } from "#src/features/cart/api.js"
import { useWretch } from "#src/hooks/api.js"
import { useInterviewState } from "#src/features/interview/hooks.js"
import {
  fetchCurrentOrEmptyCart,
  getCurrentCartId,
} from "#src/features/cart/utils.js"
import { useEvents } from "#src/features/event/hooks.js"
import { useCurrentCartStore } from "#src/features/cart/hooks.js"
import { Link as RLink } from "react-router-dom"

export const EventPage = () => {
  const { eventId = "" } = useParams()
  const wretch = useWretch()
  const events = useEvents()
  const event = events.getEvent(eventId) as Event
  const selfService = useSelfServiceLoader()
  const currentCartStore = useCurrentCartStore()

  const loc = useLocation()
  const navigate = useNavigate()

  return (
    <PageTitle title={event.name}>
      <Subtitle subtitle="Manage registrations">
        <selfService.Component
          placeholder={
            <CardGrid>
              <RegistrationCardPlaceholder />
              <RegistrationCardPlaceholder />
              <RegistrationCardPlaceholder />
            </CardGrid>
          }
        >
          {(results) => {
            return (
              <>
                <RegistrationsView
                  event={event}
                  registrations={results.registrations}
                />
                {/* Spacer only for small screens */}
                <Box
                  sx={(theme) => ({
                    display: "none",
                    [`@media (max-width: ${theme.breakpoints.sm})`]: {
                      display: "block",
                      flex: "auto",
                    },
                  })}
                />
                {results.add_options.length > 0 && (
                  <Grid
                    align="center"
                    sx={(theme) => ({
                      [`@media (max-width: ${theme.breakpoints.sm})`]: {
                        justifyContent: "center",
                      },
                    })}
                  >
                    <Grid.Col span={12} sm="content">
                      <Button
                        variant="filled"
                        leftIcon={<IconPlus />}
                        fullWidth
                        onClick={() => {
                          // show dialog
                          navigate(loc, {
                            state: {
                              ...loc.state,
                              showAddOptionsDialog: {
                                eventId: eventId,
                              },
                            },
                          })
                        }}
                      >
                        Add Registration
                      </Button>
                    </Grid.Col>
                    {currentCartStore.loader?.value?.registrations.length && (
                      <Grid.Col span="content">
                        <Anchor
                          component={RLink}
                          to={`/events/${eventId}/cart`}
                        >
                          View cart (
                          {currentCartStore.loader.value.registrations.length})
                        </Anchor>
                      </Grid.Col>
                    )}
                  </Grid>
                )}
                <OptionsDialogManager
                  eventId={eventId}
                  options={results.add_options}
                />
                <InterviewDialogManager
                  eventId={eventId}
                  onComplete={async (response, metadata) => {
                    if (metadata?.cartId && metadata.eventId) {
                      const addResponse = await wretch
                        .url(response.target_url, true)
                        .json({
                          state: response.state,
                        })
                        .post()
                        .res()

                      await addResponse.json()

                      // kind of hacky
                      const url = new URL(addResponse.url)
                      const parts = url.pathname.split("/")
                      const newCartId = parts[parts.length - 1]
                      currentCartStore.setCurrentCart(newCartId)

                      // navigate to cart page
                      navigate(`/events/${eventId}/cart`)
                    }
                  }}
                />
              </>
            )
          }}
        </selfService.Component>
      </Subtitle>
    </PageTitle>
  )
}

const RegistrationsView = observer(
  ({
    event,
    registrations,
  }: {
    event: Event
    registrations: SelfServiceRegistrationResponse[]
  }) => {
    const navigate = useNavigate()
    const loc = useLocation()
    const wretch = useWretch()
    const interviewState = useInterviewState()

    return (
      <CardGrid sx={{ minHeight: 200 }}>
        {registrations.map((r) => (
          <RegistrationCard
            key={r.registration.id}
            title={r.registration.title}
            subtitle={r.registration.subtitle}
            menuOptions={r.change_options.map((o) => ({
              id: o.id,
              label: o.name,
            }))}
            onMenuSelect={async (id) => {
              let cartId = getCurrentCartId()
              if (!cartId) {
                const [curOrEmptyCartId] = await fetchCurrentOrEmptyCart(
                  wretch,
                  event.id
                )
                cartId = curOrEmptyCartId
              }

              const state = await fetchCartInterview(
                wretch,
                cartId,
                id,
                r.registration.id
              )
              const next = await interviewState.startInterview(state, {
                cartId: cartId,
                eventId: event.id,
              })
              // show dialog
              navigate(loc, {
                state: {
                  ...loc.state,
                  showInterviewDialog: {
                    eventId: event.id,
                    recordId: next.id,
                  },
                },
              })
            }}
          >
            {r.registration.description}
          </RegistrationCard>
        ))}
      </CardGrid>
    )
  }
)

RegistrationsView.displayName = "RegistrationsView"
