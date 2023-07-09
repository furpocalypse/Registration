import { SimpleLayout } from "#src/components/layout/SimpleLayout.js"
import { SigninDialogManager } from "#src/features/auth/components/SigninDialogManager.js"
import { useAccountStore } from "#src/features/auth/hooks.js"
import { useCurrentCartStore } from "#src/features/cart/hooks.js"
import {
  CartStoreProvider,
  CurrentCartStoreProvider,
} from "#src/features/cart/providers.js"
import { useEvents } from "#src/features/event/hooks.js"
import { EventStoreProvider } from "#src/features/event/providers.js"
import { InterviewStateStoreProvider } from "#src/features/interview/routes.js"
import { listSelfServiceRegistrations } from "#src/features/selfservice/api.js"
import { SelfServiceLoaderContext } from "#src/features/selfservice/hooks.js"
import { CartPage } from "#src/features/selfservice/routes/CartPage.js"
import { EventPage } from "#src/features/selfservice/routes/EventPage.js"
import { useWretch } from "#src/hooks/api.js"
import { useLoader } from "#src/hooks/loader.js"
import { AppRoute } from "#src/routes/AppRoute.js"
import {
  LoadingOverlay,
  ShowLoadingOverlay,
} from "#src/routes/LoadingOverlay.js"
import { NotFoundPage } from "#src/routes/NotFoundPage.js"
import { Fragment, ReactNode } from "react"
import { Outlet, createBrowserRouter, useParams } from "react-router-dom"

const LayoutRoute = () => (
  <>
    <SimpleLayout>
      <Outlet />
    </SimpleLayout>
    <LoadingOverlay />
  </>
)

const SelfServiceLoader = ({
  children,
  eventId,
}: {
  children?: ReactNode
  eventId: string
}) => {
  const wretch = useWretch()
  const accountStore = useAccountStore()
  const eventStore = useEvents()
  const currentCartStore = useCurrentCartStore()
  const selfServiceLoader = useLoader(() =>
    listSelfServiceRegistrations(wretch, eventId)
  )

  const loader = useLoader(async () => {
    await accountStore.setup()
    const event = await eventStore.load(eventId)
    if (!event) {
      return null
    }
    await currentCartStore.checkAndSetCurrentCart()
    return true
  })

  return (
    <loader.Component
      placeholder={<ShowLoadingOverlay />}
      notFound={<NotFoundPage />}
    >
      <SelfServiceLoaderContext.Provider value={selfServiceLoader}>
        {children}
      </SelfServiceLoaderContext.Provider>
    </loader.Component>
  )
}

const SelfServiceAppRoute = () => {
  const { eventId = "" } = useParams()
  return (
    <>
      <InterviewStateStoreProvider>
        <EventStoreProvider>
          <CartStoreProvider>
            <Fragment key={eventId}>
              <CurrentCartStoreProvider eventId={eventId}>
                <SelfServiceLoader eventId={eventId}>
                  <Outlet />
                </SelfServiceLoader>
              </CurrentCartStoreProvider>
            </Fragment>
          </CartStoreProvider>
        </EventStoreProvider>
      </InterviewStateStoreProvider>
      <SigninDialogManager />
    </>
  )
}

export const router = createBrowserRouter([
  {
    element: <AppRoute />,
    children: [
      {
        element: <LayoutRoute />,
        children: [
          {
            element: <SelfServiceAppRoute />,
            children: [
              {
                path: "/events/:eventId",
                element: <EventPage />,
              },
              {
                path: "/events/:eventId/cart",
                element: <CartPage />,
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
])
