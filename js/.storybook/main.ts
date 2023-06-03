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
  babel: () => {
    return {
      presets: [
        "@babel/preset-env",
        [
          "@babel/preset-react",
          {
            runtime: "automatic",
          },
        ],
        "@babel/preset-typescript",
      ],
      plugins: ["@babel/plugin-transform-runtime"],
    }
  },
  webpackFinal: (config) => {
    return {
      ...config,
      cache: {
        type: "filesystem",
        cacheDirectory: path.resolve("./.cache/storybook-webpack"),
      },
      resolve: {
        ...config.resolve,
        alias: {
          ...config.resolve?.alias,

          // overridable theme file
          "#src/config/theme.js$": [
            path.resolve("./theme.ts"),
            path.resolve("./src/config/theme.ts"),
          ],

          // config.json
          "config.json$": path.resolve("./config.json"),
        },
      },
    }
  },
}
export default config
