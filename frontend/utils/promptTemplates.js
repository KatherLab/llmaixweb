/**
 * Static prompt template data, extracted from SchemaManagement.vue.
 */

// Sample document for preview
export const sampleDocument =
  'Patient Name: John Doe\nDate of Birth: 1985-03-15\nMedical Record Number: MRN-123456\n\nChief Complaint: Persistent cough and fever for 3 days\n\nHistory of Present Illness: The patient reports experiencing a dry cough that started 3 days ago...'

// Prompt templates (can be expanded later)
export const promptTemplates = {
  medical: {
    name: 'Medical Document Extraction',
    description: 'Extract structured medical information from clinical documents',
    system_prompt: `You are a medical information extraction specialist. Your task is to carefully analyze medical documents and extract structured information according to the provided JSON schema.

Important guidelines:
- Extract only information that is explicitly stated in the document
- Do not infer or assume information that is not clearly mentioned
- Use null for missing values
- Maintain medical terminology accuracy
- Preserve dates and numerical values exactly as written

Document to analyze:
{document_content}`,
    user_prompt: `Please extract the structured information from the medical document according to the JSON schema. Return only the JSON object with the extracted data.`,
  },
}
