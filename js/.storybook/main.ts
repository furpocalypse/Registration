import type { StorybookConfig } from "@storybook/react-webpack5"
import path from "path"

const config: StorybookConfig = {
  stories: [
    "../src/storybook/**/*.mdx",
    "../src/storybook/**/*.stories.@(js|jsx|ts|tsx)",
  ],
  addons: [
    "@storybook/addon-links",
    "@storybook/addon-essentials",
    "@storybook/addon-interactions",
  ],
  framework: {
    name: "@storybook/react-webpack5",
    options: {},
  },
  docs: {
    autodocs: "tag",
  },
  webpackFinal: (config) => {
    return {
      ...config,
      cache: {
        type: "filesystem",
        cacheDirectory: path.resolve("./.cache/storybook-webpack"),
      },
      module: {
        rules: [
          ...(config.module?.rules ?? []),
          {
            test: /\.svg$/,
            exclude: /node_modules/,
            use: "svgo-loader",
            type: "asset/resource",
          },
        ],
      },
      resolve: {
        ...config.resolve,
        alias: {
          ...config.resolve?.alias,

          "#src/config/theme.js$": [
            path.resolve("./theme.ts"),
            path.resolve("./src/config/theme.ts"),
          ],

          // logo
          "logo.svg$": [
            path.resolve("./logo.svg"),
            path.resolve("./resources/example-logo.svg"),
          ],

          // config.json
          "config.json$": path.resolve("./config.json"),
        },
      },
    }
  },
}
export default config
