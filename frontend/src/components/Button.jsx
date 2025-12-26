import React from 'react'
import './Button.css'

export default function Button({ children, onClick, disabled, className = '', variant, ...props }) {
  const variantClass = variant === 'secondary' ? 'secondary' : ''
  const combinedClassName = `action-button ${variantClass} ${className}`.trim()
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={combinedClassName}
      {...props}
    >
      {children}
    </button>
  )
}

