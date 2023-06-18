import {
  LoadingOverlay,
  ShowLoadingOverlay,
} from "#src/routes/LoadingOverlay.js"
import { Meta } from "@storybook/react"

export default {
  component: LoadingOverlay,
  parameters: {
    layout: "fullscreen",
  },
} as Meta<typeof LoadingOverlay>

export const Default = () => {
  return (
    <>
      <LoadingOverlay />
      <ShowLoadingOverlay />
    </>
  )
}
