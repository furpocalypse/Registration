import {
  DefaultProps,
  MantineTheme,
  MantineThemeOverride,
  Styles,
} from "@mantine/core"

import { CartProps } from "#src/features/cart/components/Cart.js"
import { LineItemProps } from "#src/features/cart/components/LineItem.js"
import { ModifierProps } from "#src/features/cart/components/Modifier.js"
import { CardGridProps } from "#src/features/selfservice/components/card/CardGrid.js"
import { RegistrationCardProps } from "#src/features/selfservice/components/card/RegistrationCard.js"
import { LoadingOverlayProps } from "#src/routes/LoadingOverlay.js"
import { AppShellLayoutProps } from "#src/components/layout/AppShellLayout.js"
import { ContainerLayoutProps } from "#src/components/layout/ContainerLayout.js"
import { HeaderProps } from "#src/components/layout/Header.js"
import { StackLayoutProps } from "#src/components/layout/StackLayout.js"
import { TitleAreaProps } from "#src/components/layout/TitleArea.js"
import { SigninDialogProps } from "#src/features/auth/components/SigninDialog.js"
import { CheckoutDialogProps } from "#src/features/checkout/components/checkout/CheckoutDialog.js"
import { OptionsDialogProps } from "#src/features/selfservice/components/options/OptionsDialog.js"
import { LogoProps } from "#src/components/layout/Logo.js"

interface Components {
  // src/components
  AppShellLayout: AppShellLayoutProps
  ContainerLayout: ContainerLayoutProps
  Header: HeaderProps
  Logo: LogoProps
  StackLayout: StackLayoutProps
  TitleArea: TitleAreaProps

  // src/features/auth/components
  SigninDialog: SigninDialogProps

  // src/features/cart/components
  Cart: CartProps
  LineItem: LineItemProps
  Modifier: ModifierProps

  // src/features/checkout/components
  CheckoutDialog: CheckoutDialogProps

  // src/features/selfservice/components
  CardGrid: CardGridProps
  RegistrationCard: RegistrationCardProps
  OptionsDialog: OptionsDialogProps

  // src/routes
  LoadingOverlay: LoadingOverlayProps
}

interface ThemeComponentOf<Props> {
  defaultProps?: Partial<Props> | ((theme: MantineTheme) => Partial<Props>)
  classNames?: Record<string, string>
  styles?: Props extends DefaultProps<infer C, infer P>
    ? Styles<C, P>
    : Styles<string>
}

type ThemeComponents = {
  [C in keyof Components]?: ThemeComponentOf<Components[C]>
} & MantineTheme["components"]

export type ThemeOverride = MantineThemeOverride & {
  components?: ThemeComponents
}
