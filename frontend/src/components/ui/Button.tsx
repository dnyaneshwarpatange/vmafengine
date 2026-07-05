import * as React from "react"
import { cn } from "@/lib/utils"

const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'default' | 'outline' | 'ghost' | 'secondary' }>(
  ({ className, variant = 'default', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 h-9 px-4 py-2",
          variant === 'default' && "bg-primary text-primary-foreground shadow hover:bg-primary/90",
          variant === 'outline' && "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
          variant === 'secondary' && "bg-secondary text-secondary-foreground hover:bg-secondary/80",
          variant === 'ghost' && "hover:bg-accent hover:text-accent-foreground",
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
