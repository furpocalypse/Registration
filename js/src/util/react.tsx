import { ReactNode } from "react"
import { createRoot } from "react-dom/client"

/**
 * Mount a React node.
 * @param appFactory - A function that returns the React node to mount.
 */
export const makeApp = (appFactory: () => ReactNode) => {
  const main = document.getElementById("main")
  if (main) {
    const root = createRoot(main)
    const app = appFactory()
    root.render(app)
  }
}
