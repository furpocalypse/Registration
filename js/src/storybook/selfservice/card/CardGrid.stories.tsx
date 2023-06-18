import { CardGrid } from "#src/features/selfservice/components/card/CardGrid.js"
import { RegistrationCard } from "#src/features/selfservice/components/card/RegistrationCard.js"
import { Meta, StoryFn } from "@storybook/react"

export default {
  component: CardGrid,
} as Meta<typeof CardGrid>

export const Default: StoryFn<typeof CardGrid> = () => {
  return (
    <CardGrid>
      {[
        <RegistrationCard key="p1" title="Person 1" subtitle="Standard">
          Example 1
        </RegistrationCard>,
        <RegistrationCard key="p2" title="Person 2" subtitle="VIP">
          Example 2<br />
          <br />
          <br />
          <br />
          <br />
          Many lines
          <br />
          <br />
        </RegistrationCard>,
        <RegistrationCard key="p3" title="Person 3" subtitle="Standard">
          Example 3
        </RegistrationCard>,
      ]}
    </CardGrid>
  )
}
