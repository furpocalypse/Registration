import { LoaderComponent } from "#src/components/loading/Loading.js"
import { useLoader } from "#src/hooks/loader.js"
import { NotFoundError } from "#src/util/loader.js"
import { Skeleton } from "@mantine/core"

export default {
  component: LoaderComponent,
}

const load =
  <T,>(value: T): (() => Promise<T>) =>
  () =>
    new Promise((r) => window.setTimeout(() => r(value), 2000))

const loadNotFound = () =>
  new Promise((_, rej) =>
    window.setTimeout(() => rej(new NotFoundError()), 2000)
  )

export const Default = () => {
  const loader = useLoader(load("Hello, world!"))
  return (
    <loader.Component placeholder={<Skeleton width={100} height={24} />}>
      {(value) => <>Loaded: {value}</>}
    </loader.Component>
  )
}

export const Not_Found = () => {
  const loader = useLoader(loadNotFound)
  return (
    <loader.Component
      placeholder={<Skeleton width={100} height={24} />}
      notFound={<>Not found</>}
    />
  )
}
