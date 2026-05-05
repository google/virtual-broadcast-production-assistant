import * as React from "react"
import { Label } from "@/components/ui/label"
import { useFormField } from "./useFormField";
import { cn } from "@/lib/utils"

export const FormLabel = React.forwardRef(({ className, ...props }, ref) => {
  const { error, formItemId } = useFormField()

  return (
    (<Label
      ref={ref}
      className={cn(error && "text-destructive", className)}
      htmlFor={formItemId}
      {...props} />)
  );
})
FormLabel.displayName = "FormLabel"
