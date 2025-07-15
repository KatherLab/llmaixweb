<template>
  <div :style="{ width: `${size}px`, height: `${size}px` }">
    <svg
      v-if="iconType === 'pdf'"
      :width="size"
      :height="size"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M7 2H17L22 7V20C22 21.1 21.1 22 20 22H4C2.9 22 2 21.1 2 20V4C2 2.9 2.9 2 4 2H7Z" fill="#E53E3E"/>
      <path d="M17 2V7H22" fill="#C53030"/>
      <text x="50%" y="70%" text-anchor="middle" fill="white" font-size="8" font-weight="bold">PDF</text>
    </svg>

    <svg
      v-else-if="iconType === 'image'"
      :width="size"
      :height="size"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" fill="#48BB78"/>
      <circle cx="8.5" cy="8.5" r="1.5" fill="white"/>
      <path d="M21 15L16 10L11 15L8 12L3 17V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V15Z" fill="#2F855A"/>
    </svg>

    <svg
      v-else-if="iconType === 'excel'"
      :width="size"
      :height="size"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M7 2H17L22 7V20C22 21.1 21.1 22 20 22H4C2.9 22 2 21.1 2 20V4C2 2.9 2.9 2 4 2H7Z" fill="#38A169"/>
      <path d="M17 2V7H22" fill="#276749"/>
      <text x="50%" y="70%" text-anchor="middle" fill="white" font-size="8" font-weight="bold">XLS</text>
    </svg>

    <svg
      v-else-if="iconType === 'csv'"
      :width="size"
      :height="size"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M7 2H17L22 7V20C22 21.1 21.1 22 20 22H4C2.9 22 2 21.1 2 20V4C2 2.9 2.9 2 4 2H7Z" fill="#4299E1"/>
      <path d="M17 2V7H22" fill="#2B6CB0"/>
      <text x="50%" y="70%" text-anchor="middle" fill="white" font-size="8" font-weight="bold">CSV</text>
    </svg>

    <svg
      v-else
      :width="size"
      :height="size"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M7 2H17L22 7V20C22 21.1 21.1 22 20 22H4C2.9 22 2 21.1 2 20V4C2 2.9 2.9 2 4 2H7Z" fill="#718096"/>
      <path d="M17 2V7H22" fill="#4A5568"/>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  fileType: {
    type: String,
    default: ''
  },
  size: {
    type: Number,
    default: 24
  }
});

const iconType = computed(() => {
  const type = props.fileType?.toLowerCase() || '';

  if (type.includes('pdf')) return 'pdf';
  if (type.includes('image') || ['jpg', 'jpeg', 'png', 'gif', 'bmp'].some(ext => type.includes(ext))) return 'image';
  if (type.includes('excel') || type.includes('xls')) return 'excel';
  if (type.includes('csv')) return 'csv';

  return 'default';
});
</script>
