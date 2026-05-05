import { Controller } from "react-hook-form";
import { FormFieldContext } from "./context";

export const FormField = (
  {
    ...props
  }
) => {
  return (
    (<FormFieldContext.Provider value={{ name: props.name }}>
      <Controller {...props} />
    </FormFieldContext.Provider>)
  );
}
