import { SimpleLayout } from "#src/components/layout/SimpleLayout.js"
import { Subtitle, Title } from "#src/components/title/Title.js"

export default {
  component: SimpleLayout,
}

export const Default = () => (
  <SimpleLayout>
    <Title title="Example Page">
      <Subtitle subtitle="Example subtitle">Page content</Subtitle>
    </Title>
  </SimpleLayout>
)
