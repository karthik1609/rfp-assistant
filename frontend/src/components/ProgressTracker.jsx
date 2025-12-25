import React from 'react'
import { usePipeline } from '../context/PipelineContext'
import './ProgressTracker.css'

const PIPELINE_STEPS = [
  { id: 'ocr', label: 'OCR', order: 1 },
  { id: 'preprocess', label: 'Preprocess', order: 2 },
  { id: 'requirements', label: 'Requirements', order: 3 },
  { id: 'build-query', label: 'Build Query', order: 4 },
  { id: 'response', label: 'Response', order: 5 },
]

export default function ProgressTracker() {
  const { statuses, confirmations, pipelineData } = usePipeline()

  const getStepStatus = (stepId) => {
    const status = statuses[stepId] || 'waiting'
    
    // Special handling for OCR: if OCR data exists, it's complete
    if (stepId === 'ocr') {
      if (pipelineData.ocr) {
        return 'complete'
      }
      return status
    }
    
    // Preprocess must be confirmed before moving to requirements
    if (stepId === 'requirements' && !confirmations.preprocessConfirmed && status === 'waiting') {
      return 'blocked'
    }
    
    // Special handling for build-query (needs requirements)
    if (stepId === 'build-query' && !pipelineData.requirements && status === 'waiting') {
      return 'blocked'
    }
    
    // Special handling for response (needs build query confirmation)
    if (stepId === 'response' && !confirmations.buildQueryConfirmed && status === 'waiting') {
      return 'blocked'
    }
    // If an explicit error state has been set, keep it
    if (status === 'error') return 'error'

    // If pipeline data for a step exists, prefer marking it complete
    // unless an explicit error state was set above.
    if (stepId === 'ocr' && pipelineData.ocr) return 'complete'
    if (stepId === 'preprocess' && pipelineData.preprocess) return 'complete'
    if (stepId === 'requirements' && pipelineData.requirements) return 'complete'
    if (stepId === 'build-query' && pipelineData.buildQuery) return 'complete'
    if (stepId === 'response' && pipelineData.response) return 'complete'

    return status
  }

  const calculateProgress = () => {
    let completed = 0
    let total = PIPELINE_STEPS.length
    
    PIPELINE_STEPS.forEach(step => {
      const stepStatus = getStepStatus(step.id)
      if (stepStatus === 'complete') {
        completed++
      }
    })
    
    return Math.round((completed / total) * 100)
  }

  const getCurrentStep = () => {
    for (const step of PIPELINE_STEPS) {
      const status = getStepStatus(step.id)
      if (status === 'processing') {
        return step
      }
      if (status === 'waiting') {
        return step
      }
    }
    return null
  }

  const progress = calculateProgress()
  const currentStep = getCurrentStep()

  return (
    <div className="progress-tracker">
      <div className="progress-header">
        <h3>Pipeline Progress</h3>
        <div className="progress-percentage">{progress}%</div>
      </div>
      
      <div className="progress-bar-container">
        <div 
          className="progress-bar-fill" 
          style={{ width: `${progress}%` }}
        />
      </div>
      
      <div className="progress-steps">
        {PIPELINE_STEPS.map((step, index) => {
          const stepStatus = getStepStatus(step.id)
          const isActive = currentStep?.id === step.id
          
          return (
            <div 
              key={step.id} 
              className={`progress-step progress-step-${stepStatus} ${isActive ? 'active' : ''}`}
            >
              <div className="step-indicator">
                {stepStatus === 'complete' && <span className="step-check">✓</span>}
                {stepStatus === 'processing' && <span className="step-spinner"></span>}
                {stepStatus === 'error' && <span className="step-error">✗</span>}
                {stepStatus === 'blocked' && <span className="step-blocked">⊘</span>}
                {(stepStatus === 'waiting' && !isActive) && <span className="step-number">{step.order}</span>}
                {isActive && stepStatus === 'waiting' && <span className="step-number">{step.order}</span>}
              </div>
              <div className="step-label">{step.label}</div>
            </div>
          )
        })}
      </div>
      
      <div className="progress-status">
        {/**
         * Show error first (so an explicit error doesn't get masked by a
         * lingering 'processing' flag). Then show response-specific
         * messages, then fall back to the current step processing message.
         */}
        {statuses['response'] === 'error' || getStepStatus('response') === 'error'
          ? 'Error generating response'
          : statuses['response'] === 'processing' || getStepStatus('response') === 'processing'
          ? 'Generating response...'
          : getStepStatus('response') === 'complete'
          ? 'Response generated'
          : currentStep && getStepStatus(currentStep.id) === 'processing'
          ? `Processing ${currentStep.label}...`
          : ''}
      </div>
    </div>
  )
}

