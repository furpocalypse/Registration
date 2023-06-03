import { Container } from "@mantine/core"
import { Title as PageTitle, Subtitle } from "#src/components/title/Title.js"
import { SimpleLayout } from "#src/components/layout/SimpleLayout.js"

export const NotFoundPage = () => {
  return (
    <SimpleLayout>
      <Container size="md">
        <PageTitle title="Not Found">
          <Subtitle subtitle="The page was not found." />
        </PageTitle>
      </Container>
    </SimpleLayout>
  )
}
