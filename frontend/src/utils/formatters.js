export function formatPreprocessOutput(preprocess) {
  if (!preprocess) return "No preprocess data available.";
  
  let output = "PREPROCESS RESULTS\n";
  output += "=".repeat(60) + "\n\n";
  
  output += "Language: " + (preprocess.language || "Unknown") + "\n\n";
  
  if (preprocess.key_requirements_summary) {
    output += "Key Requirements Summary:\n";
    output += "-".repeat(60) + "\n";
    output += preprocess.key_requirements_summary + "\n\n";
  }
  
  if (preprocess.removed_text && preprocess.removed_text.trim().length > 0) {
    output += "REMOVED TEXT (Out of Scope)\n";
    output += "-".repeat(60) + "\n";
    output += preprocess.removed_text + "\n\n";
  } else {
    output += "REMOVED TEXT: None\n\n";
  }
  
  if (preprocess.cleaned_text && preprocess.cleaned_text.trim().length > 0) {
    output += "CLEANED TEXT (Used for requirements)\n";
    output += "-".repeat(60) + "\n";
    output += preprocess.cleaned_text + "\n\n";
  } else {
    output += "CLEANED TEXT: None\n\n";
  }
  
  if (preprocess.comparison_agreement !== undefined) {
    output += "COMPARISON VALIDATION\n";
    output += "-".repeat(60) + "\n";
    output += "Agreement: " + (preprocess.comparison_agreement ? "Yes" : "No") + "\n";
    if (preprocess.comparison_notes) {
      output += "Notes: " + preprocess.comparison_notes + "\n";
    }
    output += "\n";
  }
  
  return output;
}

export function formatRequirementsOutput(requirements) {
  if (!requirements) return "No requirements data available.";
  
  let output = "REQUIREMENTS ANALYSIS\n";
  output += "=".repeat(60) + "\n\n";
  
  if (requirements.solution_requirements && requirements.solution_requirements.length > 0) {
    output += "SOLUTION REQUIREMENTS (" + requirements.solution_requirements.length + ")\n";
    output += "=".repeat(60) + "\n\n";
    requirements.solution_requirements.forEach((req, idx) => {
      output += "[" + (idx + 1) + "]\n";
      output += "-".repeat(60) + "\n";
      output += req.source_text + "\n\n";
    });
  } else {
    output += "SOLUTION REQUIREMENTS: None found\n\n";
  }
  
  if (requirements.response_structure_requirements && requirements.response_structure_requirements.length > 0) {
    output += "RESPONSE STRUCTURE REQUIREMENTS (" + requirements.response_structure_requirements.length + ")\n";
    output += "=".repeat(60) + "\n\n";
    requirements.response_structure_requirements.forEach((req, idx) => {
      output += "[" + (idx + 1) + "]\n";
      output += "-".repeat(60) + "\n";
      output += req.source_text + "\n\n";
    });
  } else {
    output += "RESPONSE STRUCTURE REQUIREMENTS: None found\n\n";
  }
  
  return output;
}

export function preprocessToEditableText(preprocess) {
  if (!preprocess) return "";
  
  let text = "=== PREPROCESS DATA ===\n\n";
  
  text += "Language: " + (preprocess.language || "en") + "\n\n";
  
  text += "=== KEY REQUIREMENTS SUMMARY ===\n";
  text += (preprocess.key_requirements_summary || "") + "\n\n";
  
  text += "=== CLEANED TEXT (Main Content) ===\n";
  text += (preprocess.cleaned_text || "") + "\n\n";
  
  text += "=== REMOVED TEXT (Out of Scope) ===\n";
  text += (preprocess.removed_text || "") + "\n\n";
  
  text += "=== COMPARISON VALIDATION ===\n";
  text += "Agreement: " + (preprocess.comparison_agreement !== false ? "Yes" : "No") + "\n";
  text += "Notes: " + (preprocess.comparison_notes || "") + "\n";
  
  return text;
}

export function parsePreprocessFromText(text) {
  if (!text || !text.trim()) {
    throw new Error("Preprocess text is empty");
  }
  
  const result = {
    language: "en",
    cleaned_text: "",
    removed_text: "",
    key_requirements_summary: "",
    comparison_agreement: true,
    comparison_notes: ""
  };
  
  const languageMatch = text.match(/Language:\s*(.+?)(?:\n|$)/i);
  if (languageMatch) {
    result.language = languageMatch[1].trim();
  }
  
  const keyReqMatch = text.match(/=== KEY REQUIREMENTS SUMMARY ===\s*\n([\s\S]*?)(?=\n===|$)/i);
  if (keyReqMatch) {
    result.key_requirements_summary = keyReqMatch[1].trim();
  }
  
  const cleanedMatch = text.match(/=== CLEANED TEXT \(Main Content\) ===\s*\n([\s\S]*?)(?=\n===|$)/i);
  if (cleanedMatch) {
    result.cleaned_text = cleanedMatch[1].trim();
  } else {
    throw new Error("Cleaned text is required and cannot be empty");
  }
  
  const removedMatch = text.match(/=== REMOVED TEXT \(Out of Scope\) ===\s*\n([\s\S]*?)(?=\n===|$)/i);
  if (removedMatch) {
    result.removed_text = removedMatch[1].trim();
  }
  
  const comparisonMatch = text.match(/=== COMPARISON VALIDATION ===\s*\n([\s\S]*?)(?=\n===|$)/i);
  if (comparisonMatch) {
    const comparisonText = comparisonMatch[1];
    const agreementMatch = comparisonText.match(/Agreement:\s*(Yes|No)/i);
    if (agreementMatch) {
      result.comparison_agreement = agreementMatch[1].toLowerCase() === "yes";
    }
    const notesMatch = comparisonText.match(/Notes:\s*(.+?)(?:\n|$)/i);
    if (notesMatch) {
      result.comparison_notes = notesMatch[1].trim();
    }
  }
  
  return result;
}

export function requirementsToEditableText(requirements) {
  if (!requirements) return "";
  
  let text = "=== REQUIREMENTS DATA ===\n\n";
  
  if (requirements.notes) {
    text += "=== NOTES ===\n";
    text += requirements.notes + "\n\n";
  }
  
  text += "=== SOLUTION REQUIREMENTS ===\n";
  if (requirements.solution_requirements && requirements.solution_requirements.length > 0) {
    requirements.solution_requirements.forEach((req, idx) => {
      text += `\n[${idx + 1}] ID: ${req.id || `SOL-${idx + 1}`}\n`;
      text += `Category: ${req.category || "General"}\n`;
      text += `Text:\n${req.source_text}\n`;
      text += "---\n";
    });
  } else {
    text += "(No solution requirements)\n";
  }
  
  text += "\n";
  
  text += "=== RESPONSE STRUCTURE REQUIREMENTS ===\n";
  if (requirements.response_structure_requirements && requirements.response_structure_requirements.length > 0) {
    requirements.response_structure_requirements.forEach((req, idx) => {
      text += `\n[${idx + 1}] ID: ${req.id || `STRUCT-${idx + 1}`}\n`;
      text += `Category: ${req.category || "General"}\n`;
      text += `Text:\n${req.source_text}\n`;
      text += "---\n";
    });
  } else {
    text += "(No response structure requirements)\n";
  }
  
  if (requirements.structure_detection) {
    text += "\n=== STRUCTURE DETECTION (Read-only) ===\n";
    text += `Has Explicit Structure: ${requirements.structure_detection.has_explicit_structure ? "Yes" : "No"}\n`;
    text += `Structure Type: ${requirements.structure_detection.structure_type || "none"}\n`;
    text += `Confidence: ${((requirements.structure_detection.confidence || 0) * 100).toFixed(0)}%\n`;
    if (requirements.structure_detection.detected_sections && requirements.structure_detection.detected_sections.length > 0) {
      text += `Sections: ${requirements.structure_detection.detected_sections.join(", ")}\n`;
    }
  }
  
  return text;
}

export function parseRequirementsFromText(text, originalRequirements = null) {
  if (!text || !text.trim()) {
    throw new Error("Requirements text is empty");
  }
  
  const result = {
    solution_requirements: [],
    response_structure_requirements: [],
    notes: "",
    structure_detection: originalRequirements?.structure_detection || null
  };
  
  const notesMatch = text.match(/=== NOTES ===\s*\n([\s\S]*?)(?=\n===|$)/i);
  if (notesMatch) {
    result.notes = notesMatch[1].trim();
  }
  
  const solutionSectionMatch = text.match(/=== SOLUTION REQUIREMENTS ===\s*\n([\s\S]*?)(?=\n=== RESPONSE STRUCTURE REQUIREMENTS ===|$)/i);
  if (solutionSectionMatch && !solutionSectionMatch[1].includes("(No solution requirements)")) {
    const solutionText = solutionSectionMatch[1];
    const requirementBlocks = solutionText.split(/\n---\n/).filter(block => block.trim());
    
    requirementBlocks.forEach((block, idx) => {
      block = block.trim();
      if (!block) return;
      
      const idMatch = block.match(/\[(\d+)\]\s*ID:\s*(.+?)(?:\n|$)/i);
      const categoryMatch = block.match(/Category:\s*(.+?)(?:\n|$)/i);
      const textMatch = block.match(/Text:\s*\n([\s\S]*?)(?=\n\[|\n---|$)/i) || block.match(/Text:\s*\n([\s\S]*)/i);
      
      if (textMatch && textMatch[1].trim()) {
        result.solution_requirements.push({
          id: idMatch ? idMatch[2].trim() : `SOL-${idx + 1}`,
          category: categoryMatch ? categoryMatch[1].trim() : "General",
          source_text: textMatch[1].trim()
        });
      }
    });
  }
  
  const structureSectionMatch = text.match(/=== RESPONSE STRUCTURE REQUIREMENTS ===\s*\n([\s\S]*?)(?=\n=== STRUCTURE DETECTION|$)/i);
  if (structureSectionMatch && !structureSectionMatch[1].includes("(No response structure requirements)")) {
    const structureText = structureSectionMatch[1];
    const requirementBlocks = structureText.split(/\n---\n/).filter(block => block.trim());
    
    requirementBlocks.forEach((block, idx) => {
      block = block.trim();
      if (!block) return;
      
      const idMatch = block.match(/\[(\d+)\]\s*ID:\s*(.+?)(?:\n|$)/i);
      const categoryMatch = block.match(/Category:\s*(.+?)(?:\n|$)/i);
      const textMatch = block.match(/Text:\s*\n([\s\S]*?)(?=\n\[|\n---|$)/i) || block.match(/Text:\s*\n([\s\S]*)/i);
      
      if (textMatch && textMatch[1].trim()) {
        result.response_structure_requirements.push({
          id: idMatch ? idMatch[2].trim() : `STRUCT-${idx + 1}`,
          category: categoryMatch ? categoryMatch[1].trim() : "General",
          source_text: textMatch[1].trim()
        });
      }
    });
  }
  
  return result;
}

export function formatDate(date) {
  if (!date) return '-';
  
  try {
    const d = new Date(date);
    if (isNaN(d.getTime())) return '-';
    
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    return '-';
  }
}

export function formatFileSize(bytes) {
  if (bytes === null || bytes === undefined || isNaN(bytes)) return '-';
  
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  const size = bytes / Math.pow(k, i);
  // Remove unnecessary decimals (if whole number, show as integer)
  const formatted = size % 1 === 0 ? Math.round(size).toString() : Math.round(size * 100) / 100;
  
  return formatted + ' ' + sizes[i];
}

export function truncateText(text, maxLength) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  
  return text.substring(0, maxLength) + '...';
}

