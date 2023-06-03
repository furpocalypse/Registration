import { listEvents } from "#src/features/event/api.js"
import { Event } from "#src/features/event/types.js"
import { Loader, NotFoundError, createLoader } from "#src/util/loader.js"
import { Wretch } from "wretch"

export class EventStore {
  loader: Loader<Map<string, Event>>

  constructor(public wretch: Wretch) {
    this.loader = createLoader(() => listEvents(wretch))
  }

  getEvent(id: string): Event | undefined {
    if (this.loader.checkLoaded()) {
      return this.loader.value.get(id)
    } else {
      return undefined
    }
  }

  load(id: string): Loader<Event> {
    return createLoader(async () => {
      const events = await this.loader
      const res = events.get(id)
      if (!res) {
        throw new NotFoundError()
      }
      return res
    })
  }
}
