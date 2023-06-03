import {
  CSSObject,
  DefaultProps,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"
import { ReactElement } from "react"
import { FunctionComponent } from "react"

type StylesFn<K extends string, P, I extends Record<K, CSSObject>> = ReturnType<
  typeof createStyles<K, P, I>
>
type Classes<F> = F extends StylesFn<infer _K, infer _P, infer _I>
  ? Extract<keyof ReturnType<F>["classes"], string>
  : string
type Params<F> = F extends StylesFn<infer _K, infer P, infer _I> ? P : never
type ParamsObj<P> = P extends Record<string, unknown>
  ? P
  : Record<string, unknown>

export const stylesHelper = <
  Props extends DefaultProps<Classes<Styles>, ParamsObj<Params<Styles>>>,
  Styles extends StylesFn<
    string,
    Record<string, unknown>,
    Record<string, CSSObject>
  >
>(
  name: string,
  styles: Styles,
  params: ((props: Props) => Params<Styles>) | null | undefined,
  component: (props: Props, styles: ReturnType<Styles>) => ReactElement | null
): FunctionComponent<Props> => {
  const Wrapped: FunctionComponent<Props> = (props) => {
    const stylesParams = params ? params(props) : {}
    const stylesResult = styles(stylesParams, {
      name: name,
      classNames: props.classNames,
      styles: props.styles,
      unstyled: props.unstyled,
    })

    return component(props, stylesResult as ReturnType<Styles>)
  }

  Wrapped.displayName = name

  return Wrapped
}

export const defaultPropsHelper = <
  Props extends Record<string, unknown>,
  Defaults extends Partial<Props>
>(
  name: string,
  defaultProps: Defaults,
  component: (
    props: Props & {
      [key in Extract<keyof Props, keyof Defaults>]-?:
        | Defaults[key]
        | NonNullable<Props[key]>
    }
  ) => ReactElement | null
): FunctionComponent<Props> => {
  const Wrapped: FunctionComponent<Props> = (props: Props) => {
    const withDefaults = useComponentDefaultProps(name, defaultProps, props)

    return component(withDefaults)
  }

  Wrapped.displayName = name

  return Wrapped
}

export const styled = <
  Props extends Record<string, unknown>,
  Defaults extends Partial<Props>,
  Styles extends StylesFn<
    string,
    Record<string, unknown>,
    Record<string, CSSObject>
  >
>(
  name: string,
  styles: Styles,
  params: ((props: Props) => Params<Styles>) | null | undefined,
  defaultProps: Defaults,
  component: (
    props: Props & {
      [key in Extract<keyof Props, keyof Defaults>]-?:
        | Defaults[key]
        | NonNullable<Props[key]>
    },
    styles: ReturnType<Styles>
  ) => ReactElement | null
): FunctionComponent<Props> => {
  const withStyles = stylesHelper(name, styles, params, component)

  const withDefaults = defaultPropsHelper<Props, Defaults>(
    name,
    defaultProps,
    withStyles
  )

  withDefaults.displayName = name

  return withDefaults
}
