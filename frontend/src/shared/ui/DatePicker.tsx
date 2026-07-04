import { forwardRef, type InputHTMLAttributes } from "react";
import { Input } from "./Input";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const DatePicker = forwardRef<HTMLInputElement, Props>(function DatePicker(props, ref) {
  return <Input ref={ref} type="date" {...props} />;
});
