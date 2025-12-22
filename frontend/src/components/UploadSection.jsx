import React, { useState } from 'react'
import { usePipeline } from '../context/PipelineContext'
import { processRFP } from '../services/api'
import './UploadSection.css'

export default function UploadSection() {
  const { updatePipelineData, updateStatus, resetPipeline } = usePipeline()
  const [files, setFiles] = useState([])
  const [status, setStatus] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files)
    setFiles(selectedFiles)
    if (selectedFiles.length > 1) {
      setStatus(`${selectedFiles.length} files selected`)
    } else {
      setStatus('')
    }
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      setStatus('Please choose at least one file first.')
      return
    }

    setIsProcessing(true)
    resetPipeline()
    // Mark OCR step as processing in the pipeline progress
    updateStatus('ocr', 'processing')
    const fileCount = files.length
    setStatus(`Uploading ${fileCount} file${fileCount > 1 ? 's' : ''} and extracting text… this may take a moment.`)

    try {
      const data = await processRFP(files)

      // Update pipeline data with OCR text only
      updatePipelineData('ocr', data.ocr_source_text || 'No OCR text returned.')
      
      // Preprocess will be run separately after user confirms/edits OCR text
      updatePipelineData('preprocess', null)
      // Mark OCR as complete, preprocess waiting
      updateStatus('ocr', 'complete')
      updateStatus('preprocess', 'waiting')

      setStatus('OCR extraction finished. Please review and confirm the OCR text to proceed.')
    } catch (err) {
      console.error(err)
      setStatus(`Failed to process files: ${err.message}`)
      updateStatus('ocr', 'error')
      updateStatus('preprocess', 'error')
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <section className="card upload-card">
      <div className="upload-header">
        <h2 className="upload-title">Upload RFP</h2>
      </div>
      <div className="upload-row">
        <input
          id="file-input"
          type="file"
          accept=".pdf,.doc,.docx,.xls,.xlsx,.txt"
          onChange={handleFileChange}
          disabled={isProcessing}
          multiple
        />
        <button
          id="upload-btn"
          onClick={handleUpload}
          disabled={isProcessing || files.length === 0}
        >
          {isProcessing ? 'Processing…' : `Upload & process${files.length > 1 ? ` (${files.length})` : ''}`}
        </button>
      </div>
      {status && (
        <div className={`status ${status.includes('Failed') ? 'error' : ''}`}>
          {status}
        </div>
      )}
    </section>
  )
}

