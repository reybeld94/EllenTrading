// src/components/ui/button.tsx
import * as React from "react"
import { cn } from "../../lib/utils"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, ...props }, ref) => (
    <button
      ref={ref}
      className={cn("inline-flex items-center px-4 py-2 text-sm font-medium bg-gray-900 text-white rounded", className)}
      {...props}
    />
  )
)

Button.displayName = "Button"
