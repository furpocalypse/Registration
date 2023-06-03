import {
  RegistrationCard,
  RegistrationCardPlaceholder,
} from "#src/features/selfservice/components/card/RegistrationCard.js"
import { Meta, StoryFn } from "@storybook/react"

export default {
  component: RegistrationCard,
  args: {
    title: "Person 1",
    subtitle: "Standard",
  },
} as Meta<typeof RegistrationCard>

export const Default: StoryFn<typeof RegistrationCard> = (args) => {
  return (
    <>
      <RegistrationCard
        menuOptions={[
          { id: "1", label: "Upgrade" },
          { id: "2", label: "Rename" },
          { id: "3", label: "Cancel" },
        ]}
        {...args}
      >
        Content
      </RegistrationCard>
    </>
  )
}

export const Placeholder = () => <RegistrationCardPlaceholder />
