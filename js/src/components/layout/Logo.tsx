import {
  DefaultProps,
  Selectors,
  createStyles,
  useComponentDefaultProps,
} from "@mantine/core"

import logoSrc from "logo.svg"

const useStyles = createStyles(() => ({
  root: {},
}))

export type LogoProps = {
  alt?: string
} & JSX.IntrinsicElements["img"] &
  DefaultProps<Selectors<typeof useStyles>>

export const Logo = (props: LogoProps) => {
  const { className, classNames, styles, unstyled, alt, src, ...other } =
    useComponentDefaultProps(
      "Logo",
      {
        alt: "Logo",
        src: logoSrc,
      },
      props
    )

  const { classes, cx } = useStyles(undefined, {
    name: "Logo",
    classNames,
    styles,
    unstyled,
  })

  return (
    <img
      className={cx(className, classes.root)}
      src={src}
      alt={alt}
      {...other}
    />
  )
}
