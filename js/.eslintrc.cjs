module.exports = {
  env: {
    browser: true,
    es2021: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:@typescript-eslint/recommended",
  ],
  overrides: [],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
  plugins: ["react", "@typescript-eslint"],
  rules: {
    "react/react-in-jsx-scope": 0,
    "@typescript-eslint/no-unused-vars": [
      "warn",
      {
        varsIgnorePattern: "_.*",
        argsIgnorePattern: "_.*",
      },
    ],
  },
  settings: {
    react: {
      version: "18",
    },
  },
  ignorePatterns: [".eslintrc.cjs", "webpack.config.cjs"],
}
