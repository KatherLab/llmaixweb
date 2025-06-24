<template>
  <div>
    <AgGridVue
      :rowData="invitations"
      :columnDefs="columnDefs"
      :defaultColDef="defaultColDef"
      :pagination="true"
      :paginationAutoPageSize="true"
      style="width: 100%; height: 400px"
      :theme="gridTheme"
      @grid-ready="onGridReady"
    >
    </AgGridVue>

    <!-- Invitation Link Modal -->
    <div
      v-if="showLinkModal"
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="closeModal"
    >
      <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full" @click.stop>
        <div class="px-6 py-5">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold text-gray-900">Invitation Link</h3>
            <button @click="closeModal" class="text-gray-400 hover:text-gray-500 transition-colors">
              <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <p class="text-sm text-gray-500 mb-4">
            Use this link to invite a user. The email will be automatically pre-filled when they open the link.
          </p>

          <div class="flex items-center mt-2">
            <input
              type="text"
              readonly
              :value="currentInvitationLink"
              class="block w-full px-4 py-2.5 text-sm text-gray-900 border border-gray-300 rounded-lg pr-10"
            />
            <button
              type="button"
              @click="copyInviteLink"
              class="ml-2 inline-flex items-center p-1.5 border border-transparent rounded-md text-blue-600 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              <span v-if="copySuccess" class="absolute bg-gray-800 text-white text-xs px-2 py-1 rounded -mt-10 ml-1">
                Copied!
              </span>
              <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-2M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
            </button>
          </div>

          <div class="mt-6 flex justify-end">
            <button
              @click="closeModal"
              class="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-lg shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, onMounted } from 'vue';
import { AgGridVue } from 'ag-grid-vue3';
import { themeMaterial } from 'ag-grid-community'; // Import Material theme

const props = defineProps({
  invitations: {
    type: Array,
    required: true
  }
});

// Modal state for invitation link
const showLinkModal = ref(false);
const currentInvitationId = ref(null);
const currentToken = ref(null);
const currentInvitationLink = ref('');
const copySuccess = ref(false);

const emit = defineEmits(['confirm-delete-invitation']);

// Create customized theme using Material
const gridTheme = themeMaterial.withParams({
  spacing: 16,
  borderRadius: 4,
  rowHeight: 56,
  headerHeight: 48,
  accentColor: '#3b82f6', // blue-500
  rowHoverColor: '#f3f4f6', // gray-100
  primaryColor: '#3b82f6', // blue-500
  cellHorizontalPadding: 16
});

const columnDefs = ref([
  {
    field: 'email',
    headerName: 'Email',
    flex: 2,
    minWidth: 200,
    cellRenderer: (params) => {
      const div = document.createElement('div');
      div.className = 'flex items-center h-full';
      div.textContent = params.value;
      return div;
    }
  },
  {
    field: 'is_used',
    headerName: 'Status',
    width: 120,
    cellRenderer: (params) => {
      const div = document.createElement('div');
      div.className = 'flex items-center h-full';
      div.innerHTML = `
        <span class="px-3 py-1.5 inline-flex text-xs leading-5 font-semibold rounded-full ${
          params.value ? 'bg-gray-100 text-gray-800' : 'bg-yellow-100 text-yellow-800'
        }">
          ${params.value ? 'Used' : 'Pending'}
        </span>
      `;
      return div;
    },
  },
  {
    field: 'actions',
    headerName: 'Actions',
    flex: 1,
    minWidth: 200,
    cellRenderer: (params) => {
      const div = document.createElement('div');
      div.className = 'flex items-center h-full justify-end gap-2';

      if (!params.data.is_used) {
        // Show Invite Link button
        const showLinkBtn = document.createElement('button');
        showLinkBtn.className = 'px-3 py-1.5 text-xs font-medium rounded text-white bg-blue-500 hover:bg-blue-600';
        showLinkBtn.textContent = 'Show Link';
        showLinkBtn.style.minWidth = '80px';
        showLinkBtn.onclick = () => {
          openLinkModal(params.data.token, params.data.id);
        };
        div.appendChild(showLinkBtn);

        // Delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'px-3 py-1.5 text-xs font-medium rounded text-white bg-red-500 hover:bg-red-600';
        deleteBtn.textContent = 'Delete';
        deleteBtn.style.minWidth = '70px';
        deleteBtn.onclick = () => {
          emit('confirm-delete-invitation', params.data);
        };
        div.appendChild(deleteBtn);
      } else {
        const usedText = document.createElement('span');
        usedText.className = 'text-xs text-gray-400';
        usedText.textContent = 'Already used';
        div.appendChild(usedText);
      }

      return div;
    }
  }
]);

// Grid API reference
const gridApi = ref(null);

// Handle grid ready event
const onGridReady = (params) => {
  gridApi.value = params.api;

  // Auto-size columns to fit the available space
  setTimeout(() => {
    params.api.sizeColumnsToFit();
  });

  // Handle window resize
  window.addEventListener('resize', () => {
    setTimeout(() => {
      params.api.sizeColumnsToFit();
    });
  });
};

const defaultColDef = ref({
  sortable: true,
  filter: true,
  resizable: true,
  cellClass: 'align-middle', // Align all cells vertically middle
});

// Open modal with invitation link
const openLinkModal = (token, id) => {
  currentToken.value = token;
  currentInvitationId.value = id;
  const baseUrl = window.location.origin;
  currentInvitationLink.value = `${baseUrl}/register?token=${token}`;
  showLinkModal.value = true;
};

// Close the modal
const closeModal = () => {
  showLinkModal.value = false;
  copySuccess.value = false;
};

// Copy invitation link to clipboard
const copyInviteLink = () => {
  // Fallback for non-secure contexts or when the Clipboard API is not available
  const copyTextFallback = (text) => {
    const textArea = document.createElement('textarea');
    textArea.value = text;

    // Make the textarea hidden
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);

    // Select the text
    textArea.focus();
    textArea.select();

    let success = false;
    try {
      // Execute the copy command
      success = document.execCommand('copy');
    } catch (err) {
      console.error('Unable to copy with fallback method', err);
    }

    // Remove the textarea
    document.body.removeChild(textArea);
    return success;
  };

  const link = currentInvitationLink.value;

  // Try the modern Clipboard API first
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(link)
      .then(() => {
        copySuccess.value = true;
        setTimeout(() => {
          copySuccess.value = false;
        }, 2000);
      })
      .catch(err => {
        console.error('Error with Clipboard API:', err);
        // Fall back to the older method
        const success = copyTextFallback(link);
        if (success) {
          copySuccess.value = true;
          setTimeout(() => {
            copySuccess.value = false;
          }, 2000);
        } else {
          alert(`Failed to copy. Please copy this link manually:\n${link}`);
        }
      });
  } else {
    // Use fallback for non-secure contexts
    const success = copyTextFallback(link);
    if (success) {
      copySuccess.value = true;
      setTimeout(() => {
        copySuccess.value = false;
      }, 2000);
    } else {
      alert(`Failed to copy. Please copy this link manually:\n${link}`);
    }
  }
};
</script>

<style>
/* Additional styling for better vertical alignment */
:deep(.ag-center-cols-container) {
  width: 100%;
}

:deep(.ag-row) {
  display: flex;
  align-items: center;
}

:deep(.ag-cell) {
  display: flex;
  align-items: center;
  height: 100% !important;
  line-height: normal;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
</style>
