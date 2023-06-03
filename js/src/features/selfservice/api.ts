import { SelfServiceRegistrationListResponse } from "#src/features/selfservice/types.js"
import { Wretch } from "wretch"
import { queryStringAddon } from "wretch/addons"

/**
 * Fetch the list of self service registrations.
 * @param wretch - The wretch instance.
 * @param eventId - The event ID, or undefined to list for all events.
 * @returns
 */
export const listSelfServiceRegistrations = async (
  wretch: Wretch,
  eventId?: string
): Promise<SelfServiceRegistrationListResponse> => {
  const res = await wretch
    .url("/self-service/registrations")
    .addon(queryStringAddon)
    .query({ event_id: eventId })
    .get()
    .json<SelfServiceRegistrationListResponse>()

  return res
}
