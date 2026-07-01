/**
 * Static schema template data + helpers, extracted from SchemaManagement.vue.
 */
import type { SchemaDefinition } from '@/types'

export interface SchemaTemplate {
  name: string
  description: string
  schema: SchemaDefinition
}

/**
 * Format a JSON value/string into a pretty-printed string.
 * @param {string|object} json
 * @returns {string}
 */
export function formatJSON(json: string | Record<string, unknown> | null | undefined): string {
  try {
    let value: unknown = json
    if (typeof json === 'string') {
      value = JSON.parse(json)
    }
    return JSON.stringify(value, null, 2)
  } catch {
    return (json as string) || '{}'
  }
}

/**
 * Starter fields seeded for a brand-new schema (matches the fields the
 * SimpleSchemaEditor used to auto-insert on mount). Seeded here — instead
 * of in the editor's onMounted — so it only applies to new schemas, not to
 * every remount caused by toggling Simple/Advanced mode.
 */
export const STARTER_SCHEMA: SchemaDefinition = {
  type: 'object',
  properties: {
    patient_name: {
      type: 'string',
      title: 'Patient Name',
      description: 'Full name of the patient',
    },
    date_of_birth: {
      type: 'string',
      format: 'date',
      title: 'Date Of Birth',
      description: 'Patient date of birth',
    },
    medical_record_number: {
      type: 'string',
      title: 'Medical Record Number',
      description: 'Unique medical record ID',
    },
  },
}

// Schema templates for medical documents
export const schemaTemplates: SchemaTemplate[] = [
  {
    name: 'Patient Information',
    description: 'Basic patient demographics and contact details',
    schema: {
      type: 'object',
      properties: {
        patient_id: { type: 'string', title: 'Patient ID' },
        first_name: { type: 'string', title: 'First Name' },
        last_name: { type: 'string', title: 'Last Name' },
        date_of_birth: { type: 'string', format: 'date', title: 'Date of Birth' },
        gender: {
          type: 'string',
          title: 'Gender',
          enum: ['Male', 'Female', 'Other'],
        },
        contact: {
          type: 'object',
          title: 'Contact Information',
          properties: {
            phone: { type: 'string', title: 'Phone Number' },
            email: { type: 'string', format: 'email', title: 'Email' },
            address: { type: 'string', title: 'Address' },
          },
        },
      },
    },
  },
  {
    name: 'Medical History',
    description: 'Patient medical history and conditions',
    schema: {
      type: 'object',
      properties: {
        conditions: {
          type: 'array',
          title: 'Medical Conditions',
          items: {
            type: 'object',
            properties: {
              condition_name: { type: 'string', title: 'Condition' },
              diagnosis_date: { type: 'string', format: 'date', title: 'Diagnosis Date' },
              status: {
                type: 'string',
                title: 'Status',
                enum: ['Active', 'Resolved', 'Chronic'],
              },
            },
          },
        },
        allergies: {
          type: 'array',
          title: 'Allergies',
          items: {
            type: 'object',
            properties: {
              allergen: { type: 'string', title: 'Allergen' },
              severity: {
                type: 'string',
                title: 'Severity',
                enum: ['Mild', 'Moderate', 'Severe'],
              },
              reaction: { type: 'string', title: 'Reaction Type' },
            },
          },
        },
        medications: {
          type: 'array',
          title: 'Current Medications',
          items: {
            type: 'object',
            properties: {
              medication_name: { type: 'string', title: 'Medication' },
              dosage: { type: 'string', title: 'Dosage' },
              frequency: { type: 'string', title: 'Frequency' },
            },
          },
        },
      },
    },
  },
  {
    name: 'Lab Results',
    description: 'Laboratory test results and measurements',
    schema: {
      type: 'object',
      properties: {
        test_date: { type: 'string', format: 'date', title: 'Test Date' },
        lab_name: { type: 'string', title: 'Laboratory Name' },
        results: {
          type: 'array',
          title: 'Test Results',
          items: {
            type: 'object',
            properties: {
              test_name: { type: 'string', title: 'Test Name' },
              value: { type: 'number', title: 'Value' },
              unit: { type: 'string', title: 'Unit' },
              reference_range: { type: 'string', title: 'Reference Range' },
              abnormal: { type: 'boolean', title: 'Abnormal' },
            },
          },
        },
      },
    },
  },
  {
    name: 'Prescription',
    description: 'Medication prescriptions and dosage information',
    schema: {
      type: 'object',
      properties: {
        prescription_date: { type: 'string', format: 'date', title: 'Prescription Date' },
        prescriber: { type: 'string', title: 'Prescriber Name' },
        medications: {
          type: 'array',
          title: 'Medications',
          items: {
            type: 'object',
            properties: {
              medication_name: { type: 'string', title: 'Medication' },
              dosage: { type: 'string', title: 'Dosage' },
              frequency: { type: 'string', title: 'Frequency' },
              duration: { type: 'string', title: 'Duration' },
              instructions: { type: 'string', title: 'Instructions' },
            },
          },
        },
      },
    },
  },
]
