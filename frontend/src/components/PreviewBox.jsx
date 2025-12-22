import React, { useEffect, useState } from 'react'
import { previewContext, getSession } from '../services/api'
import Button from './Button'
import './PreviewBox.css'

function Collapsible({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="preview-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <strong>{title}</strong>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button className="preview-toggle" onClick={() => setOpen(!open)}>{open ? 'Hide' : 'Show'}</button>
        </div>
      </div>
      {open && <div>{children}</div>}
    </div>
  )
}

export default function PreviewBox({ preprocess, requirements, buildQuery, sessionId }) {
  const [preview, setPreview] = useState(null)
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadPreview = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await previewContext(preprocess || {}, requirements || {}, { session_id: sessionId })
      setPreview(resp)
    } catch (err) {
      setError(err.message || String(err))
      setPreview(null)
    } finally {
      setLoading(false)
    }
  }

  const loadSession = async () => {
    if (!sessionId) return setSession(null)
    try {
      const s = await getSession(sessionId)
      setSession(s)
    } catch (err) {
      setSession(null)
    }
  }

  // Do not auto-fetch the preview on every prop change to avoid accidental
  // backend calls when the user confirms the build query. Preview will be
  // fetched only when the user clicks Refresh. We still load session data
  // automatically when `sessionId` becomes available.
  useEffect(() => { if (sessionId) loadSession(); }, [sessionId])

  const copyText = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      alert('Copied to clipboard')
    } catch (err) {
      alert('Copy failed')
    }
  }

  return (
    <div className="preview-box">
      <div className="preview-header">
        <div>
          <strong>LLM Preview</strong>
          <div className="preview-small">Everything the model will base questions on (including retrieval preview).</div>
        </div>
        <div className="preview-actions">
          <Button onClick={() => { loadSession(); loadPreview(); }} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</Button>
        </div>
      </div>

      {error && <div style={{ color: 'crimson' }}>Preview error: {error}</div>}

      <div className="preview-sections">
        <Collapsible title="Preprocess (cleaned text)" defaultOpen={true}>
          {preprocess ? (
            <>
              <div style={{ marginBottom: '0.5rem' }} className="preview-small">Showing cleaned/normalized text the model uses</div>
              <pre>{preprocess.cleaned_text || JSON.stringify(preprocess, null, 2)}</pre>
              <div style={{ marginTop: '0.5rem' }}>
                <Button onClick={() => copyText(preprocess.cleaned_text || JSON.stringify(preprocess, null, 2))}>Copy</Button>
              </div>
            </>
          ) : <div className="preview-small">No preprocess data available.</div>}
        </Collapsible>

        <Collapsible title="Requirements" defaultOpen={true}>
          {requirements ? (
            <>
              <pre>{JSON.stringify(requirements, null, 2)}</pre>
              <div style={{ marginTop: '0.5rem' }}>
                <Button onClick={() => copyText(JSON.stringify(requirements, null, 2))}>Copy</Button>
              </div>
            </>
          ) : <div className="preview-small">No requirements available.</div>}
        </Collapsible>

        <Collapsible title="Build Query (final prompt)" defaultOpen={true}>
          {buildQuery ? (
            <>
              <pre>{buildQuery.query_text || JSON.stringify(buildQuery, null, 2)}</pre>
              <div style={{ marginTop: '0.5rem' }}>
                <Button onClick={() => copyText(buildQuery.query_text || JSON.stringify(buildQuery, null, 2))}>Copy</Button>
              </div>
            </>
          ) : <div className="preview-small">No build query available.</div>}
        </Collapsible>

        <Collapsible title="Retrieval / RAG Preview" defaultOpen={false}>
          {preview ? (
            <>
              <div className="preview-small">Backend retrieval and context snippets the model may use.</div>
              <pre>{JSON.stringify(preview, null, 2)}</pre>
            </>
          ) : <div className="preview-small">No retrieval preview. Click Refresh to fetch.</div>}
        </Collapsible>

        <Collapsible title="Session / Q&A History" defaultOpen={false}>
          {session ? (
            <>
              <div className="preview-small">Chat session history used to enrich questions/answers.</div>
              <pre>{JSON.stringify(session, null, 2)}</pre>
            </>
          ) : <div className="preview-small">No active session or no session data.</div>}
        </Collapsible>
      </div>
    </div>
  )
}
