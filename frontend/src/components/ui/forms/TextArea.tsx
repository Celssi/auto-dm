import type { TextareaHTMLAttributes } from 'react';

interface Props extends TextareaHTMLAttributes<HTMLTextAreaElement> {}

export default function TextArea({ className = '', ...props }: Props) {
  return <textarea {...props} className={`input resize-y min-h-[5rem] ${className}`.trim()} />;
}
