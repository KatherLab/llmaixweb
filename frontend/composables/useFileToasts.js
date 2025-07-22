import { useToast } from 'vue-toastification';

export function useFileToasts() {
  const toast = useToast();

  return {
    // Success messages
    uploadSuccess: (count) => {
      toast.success(
        `Successfully uploaded ${count} file${count !== 1 ? 's' : ''}`,
        {
          timeout: 5000,
          closeOnClick: true,
          pauseOnFocusLoss: true,
          pauseOnHover: true,
          draggable: true,
          draggablePercent: 0.6,
          showCloseButtonOnHover: false,
          hideProgressBar: false,
          closeButton: "button",
          icon: true,
          rtl: false
        }
      );
    },

    deleteSuccess: (count) => {
      toast.success(
        `Deleted ${count} file${count !== 1 ? 's' : ''}`,
        { timeout: 3000 }
      );
    },

    downloadSuccess: () => {
      toast.success('Download started', { timeout: 2000 });
    },

    moveSuccess: (count) => {
      toast.success(
        `Moved ${count} file${count !== 1 ? 's' : ''} successfully`,
        { timeout: 3000 }
      );
    },

    // Warning messages
    duplicateWarning: (filename) => {
      toast.warning(
        `${filename} already exists in this project`,
        { timeout: 5000 }
      );
    },

    sizeWarning: (filename, maxSize) => {
      toast.warning(
        `${filename} exceeds the maximum file size of ${maxSize}MB`,
        { timeout: 5000 }
      );
    },

    linkedFileWarning: () => {
      toast.warning(
        'Some files are linked to other resources. Use force delete to remove them.',
        { timeout: 5000 }
      );
    },

    // Error messages
    uploadError: (filename, error) => {
      toast.error(
        `Failed to upload ${filename}: ${error}`,
        { timeout: 7000 }
      );
    },

    deleteError: (error) => {
      toast.error(
        `Failed to delete files: ${error}`,
        { timeout: 5000 }
      );
    },

    downloadError: (filename) => {
      toast.error(
        `Failed to download ${filename}`,
        { timeout: 5000 }
      );
    },

    // Info messages
    processingInfo: (action) => {
      toast.info(
        `Processing ${action}...`,
        { timeout: false, closeButton: false }
      );
    },

    queueInfo: (position, total) => {
      toast.info(
        `File ${position} of ${total} in queue`,
        { timeout: 2000 }
      );
    }
  };
}
