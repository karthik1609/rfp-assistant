import React, { useState, useEffect, useRef } from 'react'
import mammoth from 'mammoth'
import Button from './Button'
import './DocumentViewer.css'

export default function DocumentViewer({ docxBlob, onSave, onClose }) {
  const [htmlContent, setHtmlContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isSaving, setIsSaving] = useState(false)
  const contentRef = useRef(null)

  useEffect(() => {
    if (!docxBlob) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    docxBlob.arrayBuffer()
      .then((arrayBuffer) => {
        return mammoth.convertToHtml({ arrayBuffer })
      })
      .then((result) => {
        setHtmlContent(result.value)
        setLoading(false)
      })
      .catch((err) => {
        console.error('Failed to convert DOCX to HTML:', err)
        setError('Failed to load document. Please try again.')
        setLoading(false)
      })
  }, [docxBlob])

  const handleSave = async () => {
    if (!onSave) return

    setIsSaving(true)
    try {
      // Get the edited HTML content from the contentEditable div
      const editedHtml = contentRef.current?.innerHTML || htmlContent
      
      // Send the edited HTML content to the backend for conversion to DOCX
      await onSave(null, editedHtml)
      setIsSaving(false)
    } catch (err) {
      console.error('Failed to save document:', err)
      setError('Failed to save document. Please try again.')
      setIsSaving(false)
    }
  }

  const handleDownload = () => {
    if (!docxBlob) return
    
    const url = window.URL.createObjectURL(docxBlob)
    const a = document.createElement('a')
    a.href = url
    a.download = `rfp_response_${new Date().getTime()}.docx`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  if (loading) {
    return (
      <div className="document-viewer">
        <div className="document-viewer-header">
          <h2>Document Viewer</h2>
          {onClose && (
            <button className="close-btn" onClick={onClose}>×</button>
          )}
        </div>
        <div className="document-viewer-loading">
          <p>Loading document...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="document-viewer">
        <div className="document-viewer-header">
          <h2>Document Viewer</h2>
          {onClose && (
            <button className="close-btn" onClick={onClose}>×</button>
          )}
        </div>
        <div className="document-viewer-error">
          <p>{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="document-viewer">
      <div className="document-viewer-header">
        <h2>RFP Response Document</h2>
        <div className="document-viewer-actions">
          <Button 
            onClick={handleDownload}
            variant="secondary"
            disabled={!docxBlob}
          >
            Download
          </Button>
          {onSave && (
            <Button 
              onClick={handleSave}
              disabled={!docxBlob || isSaving}
            >
              {isSaving ? 'Saving...' : 'Save to Output Folder'}
            </Button>
          )}
          {onClose && (
            <button className="close-btn" onClick={onClose}>×</button>
          )}
        </div>
      </div>
      <div 
        ref={contentRef}
        className="document-viewer-content"
        contentEditable={true}
        suppressContentEditableWarning={true}
        dangerouslySetInnerHTML={{ __html: htmlContent }}
      />
    </div>
  )
}

