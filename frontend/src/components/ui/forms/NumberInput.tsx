import type { InputHTMLAttributes } from 'react';

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {}

export default function NumberInput({ className = '', ...props }: Props) {
  return <input type="number" {...props} className={`input tabular-nums ${className}`.trim()} />;
}
