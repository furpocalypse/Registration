import {
  DefaultProps,
  MantineTheme,
  MantineThemeOverride,
  Styles,
} from "@mantine/core"

import { CartProps } from "#src/features/cart/components/Cart.js"
import { LineItemProps } from "#src/features/cart/components/LineItem.js"
import { ModifierProps } from "#src/features/cart/components/Modifier.js"
import { SimpleLayoutProps } from "#src/components/layout/SimpleLayout.js"
import { CardGridProps } from "#src/features/selfservice/components/card/CardGrid.js"
import { RegistrationCardProps } from "#src/features/selfservice/components/card/RegistrationCard.js"
import { LoadingOverlayProps } from "#src/routes/LoadingOverlay.js"

interface Components {
  Cart: CartProps
  LineItem: LineItemProps
  Modifier: ModifierProps
  LoadingOverlay: LoadingOverlayProps
  SimpleLayout: SimpleLayoutProps
  CardGrid: CardGridProps
  RegistrationCard: RegistrationCardProps
  LoadingPage: LoadingOverlayProps
}

interface ThemeComponentOf<Props> {
  defaultProps?: Partial<Props> | ((theme: MantineTheme) => Partial<Props>)
  classNames?: Record<string, string>
  styles?: Props extends DefaultProps<infer C, infer P>
    ? Styles<C, P>
    : Styles<string>
}

type MappedThemeComponents = {
  [C in keyof Components]?: ThemeComponentOf<Components[C]>
}

interface ThemeComponents extends MappedThemeComponents {
  [key: string]: MantineTheme["components"][string] | undefined
}

export type ThemeOverride = MantineThemeOverride & {
  components?: ThemeComponents
}
