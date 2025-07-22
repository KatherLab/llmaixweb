<template>
  <div
    :class="[
      'flex items-center justify-center rounded-lg',
      sizeClasses[size].container
    ]"
    :style="{ backgroundColor: getFileColor(fileType).bg }"
  >
    <svg
      v-if="getFileIcon(fileType) === 'document'"
      :class="[sizeClasses[size].icon, getFileColor(fileType).text]"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
    <svg
      v-else-if="getFileIcon(fileType) === 'image'"
      :class="[sizeClasses[size].icon, getFileColor(fileType).text]"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
    <svg
      v-else-if="getFileIcon(fileType) === 'spreadsheet'"
      :class="[sizeClasses[size].icon, getFileColor(fileType).text]"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
    <svg
      v-else
      :class="[sizeClasses[size].icon, getFileColor(fileType).text]"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
  </div>
</template>

<script setup>
defineProps({
  fileType: {
    type: String,
    default: 'application/octet-stream'
  },
  size: {
    type: Number,
    default: 40
  }
});

const sizeClasses = {
  32: {
    container: 'w-8 h-8',
    icon: 'w-5 h-5'
  },
  40: {
    container: 'w-10 h-10',
    icon: 'w-6 h-6'
  },
  48: {
    container: 'w-12 h-12',
    icon: 'w-7 h-7'
  },
  64: {
    container: 'w-16 h-16',
    icon: 'w-10 h-10'
  }
};

const getFileIcon = (type) => {
  if (type?.startsWith('image/')) return 'image';
  if (type?.includes('spreadsheet') || type === 'text/csv') return 'spreadsheet';
  if (type?.includes('word') || type === 'text/plain') return 'document';
  return 'file';
};

const getFileColor = (type) => {
  if (type === 'application/pdf') return { bg: '#FEE2E2', text: 'text-red-600' };
  if (type?.startsWith('image/')) return { bg: '#DBEAFE', text: 'text-blue-600' };
  if (type?.includes('spreadsheet') || type === 'text/csv') return { bg: '#D1FAE5', text: 'text-green-600' };
  if (type?.includes('word')) return { bg: '#E0E7FF', text: 'text-indigo-600' };
  if (type === 'text/plain') return { bg: '#F3F4F6', text: 'text-gray-600' };
  return { bg: '#F9FAFB', text: 'text-gray-500' };
};
</script>
