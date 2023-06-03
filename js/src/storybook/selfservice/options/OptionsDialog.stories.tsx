import { OptionsDialog } from "#src/features/selfservice/components/options/OptionsDialog.js"
import { Meta, StoryFn } from "@storybook/react"

export default {
  component: OptionsDialog,
  args: {
    opened: true,
    options: [
      { id: "1", label: "Option 1" },
      { id: "2", label: "Option 2" },
      { id: "3", label: "Option 3" },
    ],
    onSelect: () => Promise.resolve(),
  },
} as Meta<typeof OptionsDialog>

export const Default: StoryFn<typeof OptionsDialog> = (args) => {
  return <OptionsDialog {...args} />
}
