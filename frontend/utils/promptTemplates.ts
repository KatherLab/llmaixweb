/**
 * Starter prompt templates, per language.
 *
 * A German report extracts better with German instructions, so the template
 * offered in the prompt editor follows the active UI language rather than
 * always handing out English text the user then has to translate by hand. The
 * backend applies the same rule to the instructions it appends (see
 * `utils/prompt_text.py`), so a prompt is one language end to end.
 *
 * `{document_content}` is a literal the backend substitutes — it must stay
 * untranslated in every language.
 */
import type { SupportedLocale } from '@/i18n'

export interface PromptTemplate {
  name: string
  description: string
  system_prompt: string
  user_prompt: string
}

/** Sample document used to preview a prompt, in the template's own language. */
export const sampleDocuments: Record<SupportedLocale, string> = {
  en: 'Patient Name: John Doe\nDate of Birth: 1985-03-15\nMedical Record Number: MRN-123456\n\nChief Complaint: Persistent cough and fever for 3 days\n\nHistory of Present Illness: The patient reports experiencing a dry cough that started 3 days ago...',
  de: 'Patientenname: Max Mustermann\nGeburtsdatum: 15.03.1985\nFallnummer: MRN-123456\n\nHauptbeschwerden: Anhaltender Husten und Fieber seit 3 Tagen\n\nAktuelle Anamnese: Der Patient berichtet über trockenen Husten, der vor 3 Tagen begann...',
  fr: 'Nom du patient : Jean Dupont\nDate de naissance : 15/03/1985\nNuméro de dossier : MRN-123456\n\nMotif de consultation : Toux persistante et fièvre depuis 3 jours\n\nHistoire de la maladie : Le patient rapporte une toux sèche apparue il y a 3 jours...',
  es: 'Nombre del paciente: Juan Pérez\nFecha de nacimiento: 15/03/1985\nNúmero de historia clínica: MRN-123456\n\nMotivo de consulta: Tos persistente y fiebre desde hace 3 días\n\nEnfermedad actual: El paciente refiere tos seca que comenzó hace 3 días...',
}

export const promptTemplates: Record<SupportedLocale, Record<string, PromptTemplate>> = {
  en: {
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
  },
  de: {
    medical: {
      name: 'Extraktion medizinischer Dokumente',
      description: 'Strukturierte medizinische Informationen aus klinischen Dokumenten extrahieren',
      system_prompt: `Du bist Spezialist für die Extraktion medizinischer Informationen. Deine Aufgabe ist es, medizinische Dokumente sorgfältig zu analysieren und strukturierte Informationen gemäß dem vorgegebenen JSON-Schema zu extrahieren.

Wichtige Vorgaben:
- Extrahiere ausschließlich Informationen, die ausdrücklich im Dokument stehen
- Leite nichts ab und nimm nichts an, was nicht klar genannt wird
- Verwende null für fehlende Werte
- Achte auf korrekte medizinische Fachbegriffe
- Übernimm Datumsangaben und Zahlenwerte exakt so, wie sie geschrieben sind

Zu analysierendes Dokument:
{document_content}`,
      user_prompt: `Extrahiere die strukturierten Informationen aus dem medizinischen Dokument gemäß dem JSON-Schema. Gib ausschließlich das JSON-Objekt mit den extrahierten Daten zurück.`,
    },
  },
  fr: {
    medical: {
      name: 'Extraction de documents médicaux',
      description: 'Extraire des informations médicales structurées de documents cliniques',
      system_prompt: `Vous êtes spécialiste de l'extraction d'informations médicales. Votre tâche consiste à analyser soigneusement des documents médicaux et à en extraire des informations structurées selon le schéma JSON fourni.

Consignes importantes :
- N'extrayez que les informations explicitement présentes dans le document
- Ne déduisez ni ne supposez aucune information qui ne soit clairement mentionnée
- Utilisez null pour les valeurs manquantes
- Respectez la terminologie médicale
- Reproduisez les dates et les valeurs numériques exactement telles qu'elles sont écrites

Document à analyser :
{document_content}`,
      user_prompt: `Extrayez les informations structurées du document médical selon le schéma JSON. Ne renvoyez que l'objet JSON contenant les données extraites.`,
    },
  },
  es: {
    medical: {
      name: 'Extracción de documentos médicos',
      description: 'Extraer información médica estructurada de documentos clínicos',
      system_prompt: `Eres un especialista en extracción de información médica. Tu tarea es analizar cuidadosamente documentos médicos y extraer información estructurada según el esquema JSON proporcionado.

Pautas importantes:
- Extrae únicamente la información que aparece explícitamente en el documento
- No deduzcas ni supongas información que no se mencione claramente
- Usa null para los valores ausentes
- Mantén la precisión de la terminología médica
- Conserva las fechas y los valores numéricos exactamente como están escritos

Documento a analizar:
{document_content}`,
      user_prompt: `Extrae la información estructurada del documento médico según el esquema JSON. Devuelve únicamente el objeto JSON con los datos extraídos.`,
    },
  },
}

/**
 * The line the backend puts before the JSON schema, for the prompt preview.
 *
 * Mirrors `SCHEMA_INTRO` in `backend/src/utils/prompt_text.py`. Duplicated
 * rather than fetched because it exists only to make the preview honest about
 * what gets sent; the backend remains the source of truth for the real request.
 */
export const schemaIntroPreview: Record<SupportedLocale, string> = {
  en: 'Extract the data according to this JSON schema:',
  de: 'Extrahiere die Daten gemäß diesem JSON-Schema:',
  fr: 'Extrayez les données selon ce schéma JSON :',
  es: 'Extraiga los datos según este esquema JSON:',
}

/** Templates for a language, falling back to English for anything unexpected. */
export function templatesFor(locale: string): Record<string, PromptTemplate> {
  return promptTemplates[locale as SupportedLocale] ?? promptTemplates.en
}

/** Preview document for a language, falling back to English. */
export function sampleDocumentFor(locale: string): string {
  return sampleDocuments[locale as SupportedLocale] ?? sampleDocuments.en
}
