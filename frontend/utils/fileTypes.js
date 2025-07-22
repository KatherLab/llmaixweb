export const FILE_TYPES = {
  // Documents
  'application/pdf': {
    label: 'PDF',
    icon: 'document',
    color: 'red',
    preview: true
  },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
    label: 'Word',
    icon: 'document',
    color: 'blue',
    preview: false
  },
  'application/msword': {
    label: 'Word',
    icon: 'document',
    color: 'blue',
    preview: false
  },

  // Spreadsheets
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {
    label: 'Excel',
    icon: 'spreadsheet',
    color: 'green',
    preview: false
  },
  'application/vnd.ms-excel': {
    label: 'Excel',
    icon: 'spreadsheet',
    color: 'green',
    preview: false
  },
  'text/csv': {
    label: 'CSV',
    icon: 'spreadsheet',
    color: 'green',
    preview: true
  },

  // Images
  'image/jpeg': {
    label: 'JPEG',
    icon: 'image',
    color: 'purple',
    preview: true
  },
  'image/png': {
    label: 'PNG',
    icon: 'image',
    color: 'purple',
    preview: true
  },
  'image/gif': {
    label: 'GIF',
    icon: 'image',
    color: 'purple',
    preview: true
  },
  'image/webp': {
    label: 'WebP',
    icon: 'image',
    color: 'purple',
    preview: true
  },

  // Text
  'text/plain': {
    label: 'Text',
    icon: 'document',
    color: 'gray',
    preview: true
  },
  'text/markdown': {
    label: 'Markdown',
    icon: 'document',
    color: 'gray',
    preview: true
  },

  // Default
  'application/octet-stream': {
    label: 'File',
    icon: 'file',
    color: 'gray',
    preview: false
  }
};

export function getFileTypeInfo(mimeType) {
  return FILE_TYPES[mimeType] || FILE_TYPES['application/octet-stream'];
}

export function getAcceptedFileTypes() {
  return Object.keys(FILE_TYPES)
    .filter(type => type !== 'application/octet-stream')
    .join(',');
}

export function getFileExtension(filename) {
  return filename.split('.').pop()?.toLowerCase() || '';
}

export function getMimeTypeFromExtension(extension) {
  const extMap = {
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'csv': 'text/csv',
    'txt': 'text/plain',
    'md': 'text/markdown',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp'
  };

  return extMap[extension] || 'application/octet-stream';
}
