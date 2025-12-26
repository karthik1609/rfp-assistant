import React, { useState, useEffect, useRef } from 'react'
import mammoth from 'mammoth'
import Button from './Button'
import './DocumentViewer.css'
import { storeEditMemory } from '../services/api'

// Toolbar icon components
const BoldIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/>
    <path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/>
  </svg>
)

const IncreaseSizeIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 20h18"/>
    <path d="M5 16l7-14 7 14"/>
    <path d="M8 12h6"/>
    <circle cx="18" cy="4" r="2" fill="currentColor"/>
  </svg>
)

const DecreaseSizeIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 20h18"/>
    <path d="M5 16l7-14 7 14"/>
    <path d="M8 12h6"/>
    <line x1="16" y1="3" x2="20" y2="5"/>
    <line x1="20" y1="3" x2="16" y2="5"/>
  </svg>
)

const HeaderIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/>
    <path d="M6 12h9"/>
  </svg>
)

const TableIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
    <line x1="9" y1="3" x2="9" y2="21"/>
    <line x1="15" y1="3" x2="15" y2="21"/>
    <line x1="3" y1="9" x2="21" y2="9"/>
    <line x1="3" y1="15" x2="21" y2="15"/>
  </svg>
)

const BackgroundColorIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="2" width="20" height="20" rx="2" ry="2" fill="currentColor" opacity="0.3"/>
    <path d="M6 6h12M6 12h12M6 18h12"/>
  </svg>
)

// Helper function to sanitize filename by removing invalid characters
const sanitizeFilename = (filename) => {
  if (!filename) return ''
  // Remove invalid characters for filenames: / \ : * ? " < > | and spaces
  return filename.replace(/[\/\\:*?"<>|\s]/g, '').trim()
}

// Validate filename requirements
const validateFilename = (filename) => {
  if (!filename || filename.trim() === '') {
    return { valid: true, error: null } // Empty is OK (will use default)
  }
  
  // Remove .docx extension if present for validation
  const nameWithoutExt = filename.replace(/\.docx$/i, '')
  
  if (nameWithoutExt.length === 0) {
    return { valid: false, error: 'Filename cannot be empty' }
  }
  
  // Must contain at least one letter
  if (!/[a-zA-Z]/.test(nameWithoutExt)) {
    return { valid: false, error: 'Filename must contain at least one letter' }
  }
  
  // Cannot contain spaces
  if (/\s/.test(nameWithoutExt)) {
    return { valid: false, error: 'Filename cannot contain spaces' }
  }
  
  // Cannot contain invalid characters
  if (/[\/\\:*?"<>|]/.test(nameWithoutExt)) {
    return { valid: false, error: 'Filename contains invalid characters' }
  }
  
  return { valid: true, error: null }
}

export default function DocumentViewer({ docxBlob, onSave, onClose, requirements = null }) {
  const [htmlContent, setHtmlContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [notification, setNotification] = useState(null) // For non-blocking notifications
  const [isSaving, setIsSaving] = useState(false)
  const [filename, setFilename] = useState('')
  const [filenameError, setFilenameError] = useState(null)
  const [showTableModal, setShowTableModal] = useState(false)
  const [showColorPicker, setShowColorPicker] = useState(false)
  const [colorPickerType, setColorPickerType] = useState(null) // 'cell' or 'text'
  const [tableRows, setTableRows] = useState('3')
  const [tableCols, setTableCols] = useState('3')
  const [tableError, setTableError] = useState(null)
  const contentRef = useRef(null)
  const originalHtmlRef = useRef('')
  const originalTextRef = useRef('')
  const isUpdatingContentRef = useRef(false)
  const contentInitializedRef = useRef(false)
  const scrollPositionRef = useRef({ x: 0, y: 0 })
  const savedSelectionRef = useRef(null) // Store selection for table insertion
  
  // Standard colors for color picker
  const standardColors = [
    { name: 'White', value: '#ffffff' },
    { name: 'Light Gray', value: '#f3f4f6' },
    { name: 'Gray', value: '#9ca3af' },
    { name: 'Dark Gray', value: '#4b5563' },
    { name: 'Black', value: '#000000' },
    { name: 'Red', value: '#ef4444' },
    { name: 'Blue', value: '#3b82f6' },
    { name: 'Green', value: '#22c55e' },
    { name: 'Yellow', value: '#eab308' },
    { name: 'Orange', value: '#f97316' },
  ]

  // Setup table resize functionality - defined early so it can be used in useEffect
  const setupTableResize = (table) => {
    const rows = table.querySelectorAll('tr')
    if (rows.length === 0) return
    
    const firstRow = rows[0]
    const cells = firstRow.querySelectorAll('td, th')
    
    cells.forEach((cell, index) => {
      const handle = cell.querySelector('.table-resize-handle')
      if (!handle) return
      
      // Remove existing listeners to avoid duplicates
      const newHandle = handle.cloneNode(true)
      handle.parentNode?.replaceChild(newHandle, handle)
      
      let isResizing = false
      let startX = 0
      let startWidth = 0
      let cellIndex = index
      
      const startResize = (e) => {
        isResizing = true
        startX = e.clientX
        startWidth = cell.offsetWidth
        document.addEventListener('mousemove', doResize)
        document.addEventListener('mouseup', stopResize)
        e.preventDefault()
        e.stopPropagation()
      }
      
      const doResize = (e) => {
        if (!isResizing) return
        const diff = e.clientX - startX
        const newWidth = Math.max(20, startWidth + diff) // Minimum 20px
        
        // Update all cells in this column
        rows.forEach(row => {
          const cellToResize = row.querySelectorAll('td, th')[cellIndex]
          if (cellToResize) {
            cellToResize.style.width = `${newWidth}px`
          }
        })
      }
      
      const stopResize = () => {
        isResizing = false
        document.removeEventListener('mousemove', doResize)
        document.removeEventListener('mouseup', stopResize)
      }
      
      newHandle.addEventListener('mousedown', startResize)
    })
  }

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
        originalHtmlRef.current = result.value
        // Extract plain text for comparison
        const tempDiv = document.createElement('div')
        tempDiv.innerHTML = result.value
        originalTextRef.current = tempDiv.textContent || tempDiv.innerText || ''
        setLoading(false)
        
        // Mark content as initialized after React renders it
        setTimeout(() => {
          contentInitializedRef.current = true
        }, 50)
        
        // Setup resize for existing tables after content is loaded
        setTimeout(() => {
          if (contentRef.current) {
            const existingTables = contentRef.current.querySelectorAll('table')
            existingTables.forEach(table => {
              // Add resize handles to existing tables if they don't have them
              if (!table.classList.contains('editable-table')) {
                table.classList.add('editable-table')
                table.style.tableLayout = 'fixed'
                
                const rows = table.querySelectorAll('tr')
                if (rows.length > 0) {
                  const firstRow = rows[0]
                  const cells = firstRow.querySelectorAll('td, th')
                  
                  cells.forEach((cell, index) => {
                    if (!cell.querySelector('.table-resize-handle')) {
                      cell.classList.add('editable-table-cell')
                      cell.style.position = 'relative'
                      
                      const resizeHandle = document.createElement('div')
                      resizeHandle.className = 'table-resize-handle'
                      resizeHandle.style.cssText = `
                        position: absolute;
                        top: 0;
                        right: -3px;
                        width: 6px;
                        height: 100%;
                        cursor: col-resize;
                        z-index: 10;
                        background: transparent;
                      `
                      cell.appendChild(resizeHandle)
                      
                      // Add resize handles to all cells in this column
                      rows.forEach(row => {
                        const colCell = row.querySelectorAll('td, th')[index]
                        if (colCell && colCell !== cell && !colCell.querySelector('.table-resize-handle')) {
                          colCell.classList.add('editable-table-cell')
                          colCell.style.position = 'relative'
                          const handle = resizeHandle.cloneNode(true)
                          colCell.appendChild(handle)
                        }
                      })
                    }
                  })
                  
                  setupTableResize(table)
                }
              } else {
                setupTableResize(table)
              }
            })
          }
        }, 100)
      })
      .catch((err) => {
        console.error('Failed to convert DOCX to HTML:', err)
        setError('Failed to load document. Please try again.')
        setLoading(false)
      })
  }, [docxBlob])

  // Set initial content when htmlContent is available and not yet initialized
  useEffect(() => {
    if (htmlContent && contentRef.current && !contentInitializedRef.current && !loading) {
      contentRef.current.innerHTML = htmlContent
      contentInitializedRef.current = true
    }
  }, [htmlContent, loading])

  // Handle modal open/close and scroll position
  useEffect(() => {
    if (showTableModal) {
      // Prevent body scroll
      const originalOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      
      // Focus input after modal renders (without scrolling)
      const timer = setTimeout(() => {
        const input = document.getElementById('table-rows')
        if (input) {
          input.focus({ preventScroll: true })
        }
      }, 100)
      
      return () => {
        clearTimeout(timer)
        // Restore body scroll
        document.body.style.overflow = originalOverflow
        
        // Restore scroll position after a brief delay
        setTimeout(() => {
          if (contentRef.current && scrollPositionRef.current.y !== undefined) {
            contentRef.current.scrollTop = scrollPositionRef.current.y
            contentRef.current.scrollLeft = scrollPositionRef.current.x
          }
          if (scrollPositionRef.current.bodyY !== undefined) {
            window.scrollTo(0, scrollPositionRef.current.bodyY)
          }
        }, 50)
      }
    }
  }, [showTableModal])

  // Helper function to extract plain text from HTML
  const extractTextFromHtml = (html) => {
    const tempDiv = document.createElement('div')
    tempDiv.innerHTML = html
    return tempDiv.textContent || tempDiv.innerText || ''
  }

  // Helper function to split text into sentences
  const splitIntoSentences = (text) => {
    // Split by sentence endings, but keep the punctuation
    const sentences = text.split(/([.!?]\s+)/).filter(s => s.trim().length > 0)
    const result = []
    for (let i = 0; i < sentences.length; i += 2) {
      if (i + 1 < sentences.length) {
        result.push((sentences[i] + sentences[i + 1]).trim())
      } else {
        result.push(sentences[i].trim())
      }
    }
    return result.filter(s => s.length > 0)
  }

  // Helper function to detect meaningful changes and extract only changed sentences
  const detectChanges = (originalText, editedText) => {
    // Split into sentences
    const originalSentences = splitIntoSentences(originalText)
    const editedSentences = splitIntoSentences(editedText)
    
    const changedSentences = []
    
    // Compare sentences - if they differ, mark as changed
    // Use a simple approach: compare sentence by sentence, and also check for sentences that were added/removed
    const maxSentences = Math.max(originalSentences.length, editedSentences.length)
    
    for (let i = 0; i < maxSentences; i++) {
      const origSentence = originalSentences[i] || ''
      const editedSentence = editedSentences[i] || ''
      
      // If sentences differ, include them
      if (origSentence !== editedSentence) {
        // Only include if at least one sentence exists and they're meaningfully different
        if (origSentence.trim() || editedSentence.trim()) {
          // Check if it's more than just whitespace differences
          const origClean = origSentence.replace(/\s+/g, ' ').trim()
          const editedClean = editedSentence.replace(/\s+/g, ' ').trim()
          
          if (origClean !== editedClean) {
            changedSentences.push({
              original_sentence: origSentence.trim(),
              edited_sentence: editedSentence.trim(),
              sentence_index: i
            })
          }
        }
      }
    }
    
    // Also check for sentences that were completely added or removed
    // (beyond the length of the shorter array)
    if (originalSentences.length > editedSentences.length) {
      // Some sentences were removed
      for (let i = editedSentences.length; i < originalSentences.length; i++) {
        if (originalSentences[i].trim()) {
          changedSentences.push({
            original_sentence: originalSentences[i].trim(),
            edited_sentence: '',
            sentence_index: i
          })
        }
      }
    } else if (editedSentences.length > originalSentences.length) {
      // Some sentences were added
      for (let i = originalSentences.length; i < editedSentences.length; i++) {
        if (editedSentences[i].trim()) {
          changedSentences.push({
            original_sentence: '',
            edited_sentence: editedSentences[i].trim(),
            sentence_index: i
          })
        }
      }
    }
    
    return changedSentences
  }

  const handleSave = async () => {
    if (!onSave) return

    // Validate filename if provided
    if (filename.trim()) {
      const validation = validateFilename(filename)
      if (!validation.valid) {
        setFilenameError(validation.error)
        return
      }
    }

    setIsSaving(true)
    setFilenameError(null)
    try {
      // Get the edited HTML content from the contentEditable div
      const editedHtml = contentRef.current?.innerHTML || htmlContent
      
      // Extract plain text for comparison
      const editedText = extractTextFromHtml(editedHtml)
      
      // Detect changes and store them as memories
      if (originalTextRef.current && editedText !== originalTextRef.current) {
        const sentenceChanges = detectChanges(originalTextRef.current, editedText)
        
        if (sentenceChanges.length > 0) {
          try {
            // Store edit memory with only changed sentences (much more token-efficient)
            await storeEditMemory({
              changed_sentences: sentenceChanges.slice(0, 50), // Limit number of changed sentences
              requirements_context: requirements ? {
                solution_requirements_count: requirements.solution_requirements?.length || 0,
                response_structure_requirements_count: requirements.response_structure_requirements?.length || 0,
              } : null,
            })
            console.log(`Stored ${sentenceChanges.length} changed sentences as memory`)
          } catch (err) {
            console.warn('Failed to store edit memory:', err)
            // Don't fail the save if memory storage fails
          }
        }
      }
      
      // Sanitize filename before saving (remove spaces and invalid chars)
      const sanitizedFilename = filename.trim() 
        ? sanitizeFilename(filename.trim()) 
        : null
      
      // Validate again after sanitization
      if (sanitizedFilename) {
        const validation = validateFilename(sanitizedFilename)
        if (!validation.valid) {
          setFilenameError(validation.error)
          setIsSaving(false)
          return
        }
      }
      
      // Send the edited HTML content to the backend for conversion to DOCX
      // Pass the filename if provided
      await onSave(null, editedHtml, sanitizedFilename || null)
      setIsSaving(false)
    } catch (err) {
      console.error('Failed to save document:', err)
      setError('Failed to save document. Please try again.')
      setIsSaving(false)
    }
  }

  const handleDownload = () => {
    if (!docxBlob) return
    
    // Validate filename if provided
    if (filename.trim()) {
      const validation = validateFilename(filename)
      if (!validation.valid) {
        setFilenameError(validation.error)
        return
      }
    }
    
    const url = window.URL.createObjectURL(docxBlob)
    const a = document.createElement('a')
    a.href = url
    // Use custom filename if provided, otherwise use default
    // Sanitize filename before using it (remove spaces and invalid chars)
    const sanitizedFilename = filename.trim() ? sanitizeFilename(filename.trim()) : ''
    
    // Validate again after sanitization
    if (sanitizedFilename) {
      const validation = validateFilename(sanitizedFilename)
      if (!validation.valid) {
        setFilenameError(validation.error)
        window.URL.revokeObjectURL(url)
        return
      }
    }
    
    const downloadFilename = sanitizedFilename
      ? (sanitizedFilename.endsWith('.docx') ? sanitizedFilename : `${sanitizedFilename}.docx`)
      : `rfp_response_${new Date().getTime()}.docx`
    a.download = downloadFilename
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    setFilenameError(null)
  }

  const handleFilenameChange = (e) => {
    let newValue = e.target.value
    
    // Automatically remove spaces as user types
    if (newValue.includes(' ')) {
      newValue = newValue.replace(/\s/g, '')
    }
    
    setFilename(newValue)
    
    // Clear error when user starts typing
    if (filenameError) {
      setFilenameError(null)
    }
    
    // Real-time validation feedback
    if (newValue.trim()) {
      const validation = validateFilename(newValue)
      if (!validation.valid) {
        setFilenameError(validation.error)
      } else {
        setFilenameError(null)
      }
    } else {
      setFilenameError(null)
    }
  }

  // Formatting functions
  const handleFormat = (command, value = null) => {
    document.execCommand(command, false, value)
    contentRef.current?.focus()
  }

  const handleInsertTable = (e) => {
    console.log('handleInsertTable called', { e, showTableModal })
    
    if (e) {
      e.preventDefault()
      e.stopPropagation()
    }
    
    // Store current scroll position
    if (contentRef.current) {
      scrollPositionRef.current = {
        x: contentRef.current.scrollLeft || 0,
        y: contentRef.current.scrollTop || 0
      }
    }
    
    // Store body scroll position
    scrollPositionRef.current.bodyY = window.scrollY || document.documentElement.scrollTop || 0
    
    if (!contentRef.current) {
      savedSelectionRef.current = null
    } else {
      const selection = window.getSelection()
      
      // First, try to get the current selection
      if (selection.rangeCount > 0) {
        const range = selection.getRangeAt(0)
        // Check if the selection is within our contentEditable div
        const container = range.commonAncestorContainer
        const isInContentEditable = contentRef.current.contains(container) || 
                                    container === contentRef.current ||
                                    (container.nodeType === Node.TEXT_NODE && contentRef.current.contains(container.parentElement))
        
        if (isInContentEditable) {
          // Clone the range to save it
          try {
            savedSelectionRef.current = range.cloneRange()
            console.log('Saved selection range from current selection')
          } catch (err) {
            console.warn('Failed to clone range:', err)
            savedSelectionRef.current = null
          }
        } else {
          // Selection is outside contentEditable
          savedSelectionRef.current = null
        }
      }
      
      // If we don't have a saved selection, try to find the last edit position
      if (!savedSelectionRef.current) {
        try {
          // Try to find the last meaningful position in the content
          // Look for the last text node or element
          const allNodes = []
          const walker = document.createTreeWalker(
            contentRef.current,
            NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
            null
          )
          
          let node
          while (node = walker.nextNode()) {
            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
              allNodes.push({ node, type: 'text', length: node.textContent.length })
            } else if (node.nodeType === Node.ELEMENT_NODE && node.tagName !== 'BR') {
              allNodes.push({ node, type: 'element' })
            }
          }
          
          if (allNodes.length > 0) {
            const lastNode = allNodes[allNodes.length - 1]
            const endRange = document.createRange()
            if (lastNode.type === 'text') {
              endRange.setStart(lastNode.node, lastNode.length)
            } else {
              endRange.setStartAfter(lastNode.node)
            }
            endRange.collapse(true)
            savedSelectionRef.current = endRange
            console.log('Saved range at last node position')
          } else {
            // Fallback: create range at end of contentEditable
            const endRange = document.createRange()
            endRange.selectNodeContents(contentRef.current)
            endRange.collapse(false) // Collapse to end
            savedSelectionRef.current = endRange
            console.log('Saved end range as final fallback')
          }
        } catch (err) {
          console.warn('Could not save selection:', err)
          savedSelectionRef.current = null
        }
      }
    }
    
    // Prevent body scroll when modal opens
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    
    setTableRows('3')
    setTableCols('3')
    setTableError(null)
    setShowTableModal(true)
    
    console.log('Modal state set to true')
  }

  const handleConfirmTable = () => {
    const rows = parseInt(tableRows)
    const cols = parseInt(tableCols)
    
    if (isNaN(rows) || isNaN(cols) || rows <= 0 || cols <= 0) {
      setTableError('Please enter valid numbers greater than 0')
      return
    }
    
    setTableError(null)
    // Restore body scroll before closing modal
    document.body.style.overflow = ''
    setShowTableModal(false)
    
    if (!contentRef.current) {
      setTableError('Document editor not ready. Please try again.')
      setShowTableModal(true)
      return
    }
    
    try {
      // Create the table
      const table = document.createElement('table')
      table.className = 'editable-table'
      table.style.borderCollapse = 'collapse'
      table.style.width = '100%'
      table.style.margin = '12pt 0'
      table.style.tableLayout = 'fixed'
      
      // Create rows and cells
      for (let i = 0; i < rows; i++) {
        const tr = document.createElement('tr')
        for (let j = 0; j < cols; j++) {
          const td = document.createElement('td')
          td.className = 'editable-table-cell'
          td.style.border = '1px solid #d1d5db'
          td.style.padding = '8pt'
          td.style.verticalAlign = 'top'
          td.style.position = 'relative'
          td.innerHTML = '&nbsp;'
          
          // Add resize handle
          const resizeHandle = document.createElement('div')
          resizeHandle.className = 'table-resize-handle'
          resizeHandle.style.cssText = `
            position: absolute;
            top: 0;
            right: -3px;
            width: 6px;
            height: 100%;
            cursor: col-resize;
            z-index: 10;
            background: transparent;
          `
          td.appendChild(resizeHandle)
          tr.appendChild(td)
        }
        table.appendChild(tr)
      }
      
      // Restore focus to contentEditable
      if (contentRef.current) {
        contentRef.current.focus()
      }
      
      // Get the selection object
      const selection = window.getSelection()
      
      // Use the saved selection range if available
      let inserted = false
      if (savedSelectionRef.current && contentRef.current) {
        try {
          const savedRange = savedSelectionRef.current
          const container = savedRange.commonAncestorContainer
          
          if (contentRef.current.contains(container) || container === contentRef.current) {
            selection.removeAllRanges()
            selection.addRange(savedRange)
            
            savedRange.insertNode(table)
            inserted = true
            
            const newRange = document.createRange()
            newRange.setStartAfter(table)
            newRange.collapse(true)
            selection.removeAllRanges()
            selection.addRange(newRange)
            
            console.log('Table inserted at saved cursor position')
          } else {
            console.warn('Saved range is no longer valid, using fallback')
          }
        } catch (err) {
          console.warn('Failed to use saved range:', err)
        }
      }
      
      if (!inserted && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0)
        
        // Check if range is within our contentEditable div
        if (contentRef.current && contentRef.current.contains(range.commonAncestorContainer)) {
          try {
            // Insert table at cursor position
            range.insertNode(table)
            inserted = true
            
            // Move cursor after the table
            const newRange = document.createRange()
            newRange.setStartAfter(table)
            newRange.collapse(true)
            selection.removeAllRanges()
            selection.addRange(newRange)
            
            console.log('Table inserted at current selection')
          } catch (err) {
            console.warn('Failed to insert at current selection:', err)
          }
        }
      }
      
      // Final fallback: Insert at end of content
      if (!inserted) {
        console.log('Using fallback: inserting at end')
        // Create a paragraph if content is empty
        if (!contentRef.current.hasChildNodes() || contentRef.current.textContent.trim() === '') {
          const p = document.createElement('p')
          p.appendChild(table)
          contentRef.current.appendChild(p)
        } else {
          // Insert after last child or append
          const lastChild = contentRef.current.lastElementChild || contentRef.current.lastChild
          if (lastChild && lastChild.nodeType === Node.ELEMENT_NODE) {
            // Insert after last element
            const p = document.createElement('p')
            p.appendChild(table)
            contentRef.current.appendChild(p)
          } else {
            contentRef.current.appendChild(table)
          }
        }
        
        // Set cursor after table
        const newRange = document.createRange()
        newRange.setStartAfter(table)
        newRange.collapse(true)
        selection.removeAllRanges()
        selection.addRange(newRange)
      }
      
      // Clear saved selection after use
      savedSelectionRef.current = null
      
      // Setup resize functionality
      setTimeout(() => {
        setupTableResize(table)
      }, 0)
      
      // Focus the editor
      contentRef.current.focus()
      
    } catch (err) {
      console.error('Error inserting table:', err)
      setTableError('Failed to insert table. Please try again.')
      setShowTableModal(true)
    }
  }


  const handleTableBackgroundColor = () => {
    const selection = window.getSelection()
    if (selection.rangeCount > 0) {
      const range = selection.getRangeAt(0)
      let container = range.commonAncestorContainer
      
      if (container.nodeType === Node.TEXT_NODE) {
        container = container.parentElement
      }
      
      // Find the table cell
      let cell = container
      while (cell && cell.tagName !== 'TD' && cell.tagName !== 'TH' && cell !== contentRef.current) {
        cell = cell.parentElement
      }
      
      if (cell && (cell.tagName === 'TD' || cell.tagName === 'TH')) {
        setColorPickerType('cell')
        setShowColorPicker(true)
      } else {
        // Show error notification
        setNotification('Please select text inside a table cell first.')
        setTimeout(() => setNotification(null), 3000)
      }
    } else {
      setNotification('Please select text inside a table cell first.')
      setTimeout(() => setNotification(null), 3000)
    }
    contentRef.current?.focus()
  }

  const handleTextColor = () => {
    const selection = window.getSelection()
    if (selection.rangeCount > 0 && selection.toString().trim()) {
      setColorPickerType('text')
      setShowColorPicker(true)
    } else {
      setNotification('Please select text to change its color.')
      setTimeout(() => setNotification(null), 3000)
    }
    contentRef.current?.focus()
  }

  const handleColorSelect = (color) => {
    const selection = window.getSelection()
    
    if (colorPickerType === 'cell') {
      if (selection.rangeCount > 0) {
        const range = selection.getRangeAt(0)
        let container = range.commonAncestorContainer
        
        if (container.nodeType === Node.TEXT_NODE) {
          container = container.parentElement
        }
        
        let cell = container
        while (cell && cell.tagName !== 'TD' && cell.tagName !== 'TH' && cell !== contentRef.current) {
          cell = cell.parentElement
        }
        
        if (cell && (cell.tagName === 'TD' || cell.tagName === 'TH')) {
          cell.style.backgroundColor = color
        }
      }
      } else if (colorPickerType === 'text') {
        if (selection.rangeCount > 0 && selection.toString().trim()) {
          const range = selection.getRangeAt(0)
          const span = document.createElement('span')
          span.style.color = color
          try {
            range.surroundContents(span)
          } catch (e) {
            // If surroundContents fails, try a different approach
            const contents = range.extractContents()
            span.appendChild(contents)
            range.insertNode(span)
          }
        }
      }
    
    setShowColorPicker(false)
    setColorPickerType(null)
    contentRef.current?.focus()
  }

  const handleHeader = (level) => {
    const selection = window.getSelection()
    if (selection.rangeCount > 0) {
      const range = selection.getRangeAt(0)
      const selectedText = range.toString().trim()
      
      if (selectedText) {
        // Wrap selected text in header
        const header = document.createElement(`h${level}`)
        header.textContent = selectedText
        range.deleteContents()
        range.insertNode(header)
        // Move cursor after header
        const newRange = document.createRange()
        newRange.setStartAfter(header)
        newRange.collapse(true)
        selection.removeAllRanges()
        selection.addRange(newRange)
      } else {
        // If no selection, try to wrap the current paragraph or create new header
        let node = range.commonAncestorContainer
        if (node.nodeType === Node.TEXT_NODE) {
          node = node.parentElement
        }
        
        // If it's already a header, change the level
        if (node && /^H[1-6]$/i.test(node.tagName)) {
          const header = document.createElement(`h${level}`)
          header.innerHTML = node.innerHTML
          node.parentNode?.replaceChild(header, node)
        } else if (node && (node.tagName === 'P' || node.tagName === 'DIV')) {
          // Wrap paragraph in header
          const header = document.createElement(`h${level}`)
          header.innerHTML = node.innerHTML || '&nbsp;'
          node.parentNode?.replaceChild(header, node)
        } else {
          // Create new header at cursor
          const header = document.createElement(`h${level}`)
          header.innerHTML = '&nbsp;'
          range.insertNode(header)
          // Move cursor inside header
          const newRange = document.createRange()
          newRange.setStart(header, 0)
          newRange.collapse(true)
          selection.removeAllRanges()
          selection.addRange(newRange)
        }
      }
    }
    contentRef.current?.focus()
  }

  const handleFontSize = (increase) => {
    const currentSize = document.queryCommandValue('fontSize') || '3'
    const newSize = increase 
      ? Math.min(parseInt(currentSize) + 1, 7) 
      : Math.max(parseInt(currentSize) - 1, 1)
    document.execCommand('fontSize', false, newSize)
    contentRef.current?.focus()
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
          <div className="filename-input-group">
            <div className="filename-input-wrapper">
              <input
                id="filename-input"
                type="text"
                className={`filename-input ${filenameError ? 'filename-input-error' : ''}`}
                value={filename}
                onChange={handleFilenameChange}
                placeholder="Choose your filename"
              />
              {filenameError && (
                <span className="filename-error-message">{filenameError}</span>
              )}
            </div>
            <div className="filename-actions">
              <Button 
                onClick={handleDownload}
                variant="secondary"
                disabled={!docxBlob || (filename.trim() && filenameError)}
              >
                Download
              </Button>
              {onSave && (
                <Button 
                  onClick={handleSave}
                  disabled={!docxBlob || isSaving || (filename.trim() && filenameError)}
                >
                  {isSaving ? 'Saving...' : 'Save to Output Folder'}
                </Button>
              )}
            </div>
          </div>
          {onClose && (
            <button className="close-btn" onClick={onClose}>×</button>
          )}
        </div>
      </div>
      <div className="document-editor-toolbar">
        <div className="toolbar-group">
          <button
            type="button"
            className="toolbar-btn"
            onClick={() => handleFormat('bold')}
            title="Bold (Ctrl+B)"
          >
            <BoldIcon />
            <span>Bold</span>
          </button>
        </div>
        <div className="toolbar-group">
          <button
            type="button"
            className="toolbar-btn"
            onClick={() => handleFontSize(false)}
            title="Decrease font size"
          >
            <DecreaseSizeIcon />
            <span>Smaller</span>
          </button>
          <button
            type="button"
            className="toolbar-btn"
            onClick={() => handleFontSize(true)}
            title="Increase font size"
          >
            <IncreaseSizeIcon />
            <span>Larger</span>
          </button>
        </div>
        <div className="toolbar-group">
          <button
            type="button"
            className="toolbar-btn"
            onClick={() => handleHeader(1)}
            title="Heading 1"
          >
            <HeaderIcon />
            <span>H1</span>
          </button>
          <button
            type="button"
            className="toolbar-btn"
            onClick={() => handleHeader(2)}
            title="Heading 2"
          >
            <HeaderIcon />
            <span>H2</span>
          </button>
          <button
            type="button"
            className="toolbar-btn"
            onClick={() => handleHeader(3)}
            title="Heading 3"
          >
            <HeaderIcon />
            <span>H3</span>
          </button>
        </div>
        <div className="toolbar-group">
          <button
            type="button"
            className="toolbar-btn"
            onClick={handleInsertTable}
            onMouseDown={(e) => {
              // Prevent any default behavior on mousedown
              e.preventDefault()
            }}
            title="Insert table"
          >
            <TableIcon />
            <span>Table</span>
          </button>
          <button
            type="button"
            className="toolbar-btn"
            onClick={handleTableBackgroundColor}
            title="Set table cell background color"
          >
            <BackgroundColorIcon />
            <span>Cell Color</span>
          </button>
          <button
            type="button"
            className="toolbar-btn"
            onClick={handleTextColor}
            title="Set text color"
          >
            <BackgroundColorIcon />
            <span>Text Color</span>
          </button>
        </div>
      </div>
      <div 
        ref={contentRef}
        className="document-viewer-content"
        contentEditable={true}
        suppressContentEditableWarning={true}
        onKeyDown={(e) => {
          // Handle Ctrl+B for bold
          if (e.ctrlKey && e.key === 'b') {
            e.preventDefault()
            handleFormat('bold')
          }
        }}
        onMouseUp={() => {
          // Save selection whenever user clicks in the editor
          const selection = window.getSelection()
          if (selection.rangeCount > 0 && contentRef.current) {
            const range = selection.getRangeAt(0)
            const container = range.commonAncestorContainer
            if (contentRef.current.contains(container) || container === contentRef.current) {
              try {
                savedSelectionRef.current = range.cloneRange()
              } catch (err) {
                // Ignore errors
              }
            }
          }
        }}
        onKeyUp={() => {
          // Save selection whenever user types or moves cursor
          const selection = window.getSelection()
          if (selection.rangeCount > 0 && contentRef.current) {
            const range = selection.getRangeAt(0)
            const container = range.commonAncestorContainer
            if (contentRef.current.contains(container) || container === contentRef.current) {
              try {
                savedSelectionRef.current = range.cloneRange()
              } catch (err) {
                // Ignore errors
              }
            }
          }
        }}
      />
      
      {/* Table Dimensions Modal */}
      {showTableModal && (
        <div 
          className="modal-overlay" 
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            // Restore body scroll before closing
            document.body.style.overflow = ''
            setShowTableModal(false)
          }}
          onMouseDown={(e) => {
            // Prevent any scroll when clicking overlay
            e.preventDefault()
          }}
        >
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Insert Table</h3>
              <button 
                className="modal-close" 
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  // Restore body scroll before closing
                  document.body.style.overflow = ''
                  setShowTableModal(false)
                }}
              >×</button>
            </div>
            <div className="modal-body">
              <div className="modal-input-group">
                <label htmlFor="table-rows">Number of Rows:</label>
                <input
                  id="table-rows"
                  type="number"
                  min="1"
                  max="50"
                  value={tableRows}
                  onChange={(e) => {
                    setTableRows(e.target.value)
                    setTableError(null)
                  }}
                  className="modal-input"
                />
              </div>
              <div className="modal-input-group">
                <label htmlFor="table-cols">Number of Columns:</label>
                <input
                  id="table-cols"
                  type="number"
                  min="1"
                  max="50"
                  value={tableCols}
                  onChange={(e) => {
                    setTableCols(e.target.value)
                    setTableError(null)
                  }}
                  className="modal-input"
                />
              </div>
              {tableError && (
                <div className="modal-error">{tableError}</div>
              )}
            </div>
            <div className="modal-footer">
              <Button 
                variant="secondary" 
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  // Restore body scroll before closing
                  document.body.style.overflow = ''
                  setShowTableModal(false)
                }}
              >
                Cancel
              </Button>
              <Button 
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  handleConfirmTable()
                }}
              >
                Insert Table
              </Button>
            </div>
          </div>
        </div>
      )}
      
      {/* Color Picker Modal */}
      {showColorPicker && (
        <div className="modal-overlay" onClick={() => {
          setShowColorPicker(false)
          setColorPickerType(null)
        }}>
          <div className="color-picker-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{colorPickerType === 'cell' ? 'Cell Background Color' : 'Text Color'}</h3>
              <button className="modal-close" onClick={() => {
                setShowColorPicker(false)
                setColorPickerType(null)
              }}>×</button>
            </div>
            <div className="color-picker-body">
              <div className="color-grid">
                {standardColors.map((color) => (
                  <button
                    key={color.value}
                    className="color-option"
                    onClick={() => handleColorSelect(color.value)}
                    title={color.name}
                  >
                    <div className="color-box" style={{ backgroundColor: color.value }}></div>
                    <span className="color-name">{color.name}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Error Notification */}
      {error && (
        <div className="notification error-notification">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}
      
      {/* General Notification (non-blocking) */}
      {notification && (
        <div className="notification error-notification">
          <span>{notification}</span>
          <button onClick={() => setNotification(null)}>×</button>
        </div>
      )}
    </div>
  )
}

