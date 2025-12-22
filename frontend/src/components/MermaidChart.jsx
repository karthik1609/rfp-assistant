import React, { useEffect, useRef } from 'react'
import mermaid from 'mermaid'

export default function MermaidChart({ code, className }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!code) {
      if (ref.current) ref.current.innerHTML = ''
      return
    }

    mermaid.initialize({ startOnLoad: false, theme: 'default' })

    const id = 'mermaid-' + Math.random().toString(36).slice(2, 9)
    try {
      mermaid.mermaidAPI.render(id, code, (svgCode) => {
        if (ref.current) ref.current.innerHTML = svgCode
      })
    } catch (err) {
      if (ref.current) ref.current.innerText = 'Mermaid render error: ' + err.message
    }
  }, [code])

  return <div ref={ref} className={className} />
}
