import { AppShellLayout } from "#src/components/layout/AppShellLayout.js"
import { ContainerLayout } from "#src/components/layout/ContainerLayout.js"
import { StackLayout } from "#src/components/layout/StackLayout.js"
import { ReactNode } from "react"

export const SimpleLayout = ({ children }: { children?: ReactNode }) => (
  <AppShellLayout>
    <ContainerLayout>
      <StackLayout>{children}</StackLayout>
    </ContainerLayout>
  </AppShellLayout>
)
