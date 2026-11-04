import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
  children: React.ReactNode
  icon?: React.ReactNode
}

export function Button({
  variant = 'primary',
  children,
  icon,
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button className={`button ${variant} ${className}`} {...props}>
      {icon}
      {children}
    </button>
  )
}

