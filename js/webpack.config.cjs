const path = require("path")
const HtmlWebpackPlugin = require("html-webpack-plugin")

module.exports = (env, argv) => {
  const prod = argv.mode !== "development"

  return {
    mode: prod ? "production" : "development",
    entry: {
      selfservice: "./src/features/selfservice/index.tsx",
    },
    output: {
      publicPath: "/", // TODO: make configurable
      filename: prod ? "assets/js/[name].[contenthash].bundle.js" : undefined,
      path: path.resolve("./dist"),
      clean: prod,
    },
    module: {
      rules: [
        // babel-loader for all js/ts source files
        {
          test: /\.[tj]sx?$/,
          exclude: /node_modules/,
          use: "babel-loader",
        },

        // config.json
        {
          test: /config\.json$/,
          type: "asset/resource",
          generator: {
            filename: "config.json",
          },
        },
      ],
    },
    resolve: {
      alias: {
        // overridable theme file
        "#src/config/theme.js$": [
          path.resolve("./theme.ts"),
          path.resolve("./src/config/theme.ts"),
        ],

        // config.json
        "config.json$": path.resolve("./config.json"),
      },
    },
    plugins: [
      // html page for each entry point
      new HtmlWebpackPlugin({
        title: "Registration",
        template: "./src/index.html",
        chunks: ["selfservice"],
      }),
    ],
    // source map config
    devtool: prod ? false : "eval-cheap-source-map",
    devServer: {
      historyApiFallback: {
        rewrites: [],
      },
      port: 9000,
    },
    cache: {
      // cache on filesystem for CI and to reduce memory usage
      type: "filesystem",
      cacheDirectory: path.resolve("./.cache/webpack"),
    },
    optimization: {
      splitChunks: {
        chunks: prod ? "all" : undefined,
      },
    },
  }
}
