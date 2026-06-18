import type { InputHTMLAttributes } from 'react';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  inputClassName?: string;
}

export default function TextInput({ className = '', inputClassName = '', ...props }: Props) {
  return <input {...props} className={`input ${inputClassName} ${className}`.trim()} />;
}
