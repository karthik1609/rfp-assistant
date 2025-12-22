import React, { useState } from 'react'
import './ResponsePreview.css'
import MermaidChart from './MermaidChart'

export default function ResponsePreview({ responses, onEdit, onExport, onClose }) {
  const [editingId, setEditingId] = useState(null)
  const [editedResponses, setEditedResponses] = useState({})
  const [showDiff, setShowDiff] = useState({})

  const handleEdit = (responseId, originalText) => {
    setEditingId(responseId)
    if (!editedResponses[responseId]) {
      setEditedResponses(prev => ({ ...prev, [responseId]: originalText }))
    }
  }

  const handleSave = (responseId) => {
    setEditingId(null)
    if (onEdit && editedResponses[responseId]) {
      onEdit(responseId, editedResponses[responseId])
    }
  }

  const handleCancel = (responseId, originalText) => {
    setEditingId(null)
    setEditedResponses(prev => {
      const newState = { ...prev }
      delete newState[responseId]
      return newState
    })
    setShowDiff(prev => {
      const newState = { ...prev }
      delete newState[responseId]
      return newState
    })
  }

  const toggleDiff = (responseId, originalText) => {
    setShowDiff(prev => ({
      ...prev,
      [responseId]: !prev[responseId]
    }))
  }

  return (
    <div className="response-preview-overlay">
      <div className="response-preview-modal">
        <div className="preview-header">
          <h2>Response Preview</h2>
          <div className="preview-actions">
            <select className="export-format-select" id="export-format" defaultValue="pdf">
              <option value="pdf">PDF</option>
              <option value="docx">DOCX</option>
              <option value="markdown">Markdown</option>
            </select>
            <button className="export-btn" onClick={() => {
              const format = document.getElementById('export-format').value
              onExport(format)
            }}>
              Export
            </button>
            {onClose && (
              <button className="close-btn" onClick={onClose}>×</button>
            )}
          </div>
        </div>
        
        <div className="preview-content">
          {responses && responses.length > 0 ? (
            responses.map((resp, idx) => {
              const isEditing = editingId === resp.requirement_id
              const editedText = editedResponses[resp.requirement_id] || resp.response
              const hasEdits = editedResponses[resp.requirement_id] && 
                              editedResponses[resp.requirement_id] !== resp.response
              
              return (
                <div key={resp.requirement_id || idx} className="preview-item">
                  <div className="preview-item-header">
                    <div>
                      <h3>Requirement {idx + 1}: {resp.requirement_id}</h3>
                      {resp.quality && (
                        <div className="quality-indicator">
                          <span className={`quality-score quality-${resp.quality.completeness}`}>
                            Quality: {resp.quality.score.toFixed(0)}/100
                          </span>
                          <span className={`quality-badge quality-${resp.quality.completeness}`}>
                            {resp.quality.completeness}
                          </span>
                          <span className={`quality-badge quality-${resp.quality.relevance}`}>
                            {resp.quality.relevance} relevance
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="item-actions">
                      {hasEdits && (
                        <button 
                          className="diff-btn"
                          onClick={() => toggleDiff(resp.requirement_id, resp.response)}
                        >
                          {showDiff[resp.requirement_id] ? 'Hide' : 'Show'} Diff
                        </button>
                      )}
                      {!isEditing ? (
                        <button 
                          className="edit-btn"
                          onClick={() => handleEdit(resp.requirement_id, resp.response)}
                        >
                          Edit
                        </button>
                      ) : (
                        <>
                          <button 
                            className="save-btn"
                            onClick={() => handleSave(resp.requirement_id)}
                          >
                            Save
                          </button>
                          <button 
                            className="cancel-btn"
                            onClick={() => handleCancel(resp.requirement_id, resp.response)}
                          >
                            Cancel
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                  
                  <div className="preview-item-content">
                    {showDiff[resp.requirement_id] && hasEdits ? (
                      <div className="diff-view">
                        <div className="diff-original">
                          <h4>Original:</h4>
                          {renderResponseWithMermaid(resp.response)}
                        </div>
                        <div className="diff-edited">
                          <h4>Edited:</h4>
                          {renderResponseWithMermaid(editedText)}
                        </div>
                      </div>
                    ) : isEditing ? (
                      <textarea
                        className="edit-textarea"
                        value={editedText}
                        onChange={(e) => setEditedResponses(prev => ({
                          ...prev,
                          [resp.requirement_id]: e.target.value
                        }))}
                        rows={15}
                      />
                    ) : (
                      <div className="response-text">
                        {hasEdits ? (
                          <>
                            <span className="edited-badge">Edited</span>
                            {renderResponseWithMermaid(editedText)}
                          </>
                        ) : (
                          renderResponseWithMermaid(resp.response)
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })
          ) : (
            <div className="preview-empty">
              <p>No responses to preview</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function splitResponseWithMermaid(text) {
  const parts = []
  if (!text) return parts

  const fencedRe = /```mermaid\n([\s\S]*?)```/g
  let lastIndex = 0
  let m
  const spans = []
  while ((m = fencedRe.exec(text)) !== null) {
    spans.push({ start: m.index, end: m.index + m[0].length, code: m[1], caption: null })
  }

  if (spans.length === 0) {
    const standaloneRe = /(^|\n)\s*((?:flowchart|graph|sequenceDiagram|gantt|classDiagram|stateDiagram|pie)[\s\S]*?)(?:\nCaption:\s*(.*?))?(?=\n\n|$)/im
    let remaining = text
    let baseOffset = 0
    while (true) {
      const sm = remaining.match(standaloneRe)
      if (!sm) break
      const matchIndex = sm.index || 0
      const pre = remaining.slice(0, matchIndex)
      if (pre && pre.trim()) parts.push({ type: 'text', content: pre })
      let diagramCode = sm[2] || ''
      const caption = sm[3] || null

      const lines = diagramCode.split('\n')
      let minIndent = Infinity
      for (const ln of lines) {
        if (ln.trim() === '') continue
        const m = ln.match(/^\s*/)
        if (m) minIndent = Math.min(minIndent, m[0].length)
      }
      if (!isFinite(minIndent) || minIndent === 0) {
      } else {
        for (let i = 0; i < lines.length; i++) {
          lines[i] = lines[i].slice(minIndent)
        }
        diagramCode = lines.join('\n')
      }

      parts.push({ type: 'mermaid', content: diagramCode.trim(), caption })
      const advance = matchIndex + (sm[0] ? sm[0].length : 0)
      remaining = remaining.slice(advance)
      baseOffset += advance
    }
    if (remaining && remaining.trim()) parts.push({ type: 'text', content: remaining })
    return parts
  }

  // If there are fenced spans, build parts around them
  let cursor = 0
  for (const span of spans) {
    if (span.start > cursor) {
      parts.push({ type: 'text', content: text.slice(cursor, span.start) })
    }
    parts.push({ type: 'mermaid', content: span.code.trim(), caption: null })
    cursor = span.end
  }
  if (cursor < text.length) parts.push({ type: 'text', content: text.slice(cursor) })
  return parts
}

function renderResponseWithMermaid(text) {
  const parts = splitResponseWithMermaid(text)
  if (!parts || parts.length === 0) return <pre>{text}</pre>

  return parts.map((p, i) => {
    if (p.type === 'text') return <pre key={i}>{p.content}</pre>
    return (
      <div key={i} className="mermaid-wrapper">
        <MermaidChart code={p.content} className="mermaid-chart" />
        {p.caption ? <div className="mermaid-caption">{p.caption}</div> : null}
      </div>
    )
  })
}

