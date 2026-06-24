/**
 * Composable for triggering browser file downloads from blob data.
 * Replaces the copy-pasted createObjectURL -> anchor -> click -> revoke sequence
 * found across DownloadModal, DocumentsManagement, ViewDocumentGroupModal,
 * MetricsExportModal, etc.
 *
 * Usage:
 *   const { downloadBlob } = useFileDownload()
 *   downloadBlob(response.data, 'results.zip')
 *   // or from an API call directly:
 *   await downloadFromApi(() => api.get(url, { responseType: 'blob' }), 'file.pdf')
 */
export function useFileDownload() {
  /**
   * Trigger a download from raw blob data.
   * @param {Blob|ArrayBuffer} data - The file data
   * @param {string} filename - Suggested download filename
   * @param {string} [mimeType] - Optional MIME type override
   */
  function downloadBlob(data, filename, mimeType) {
    const blob = mimeType ? new Blob([data], { type: mimeType }) : new Blob([data])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  /**
   * Fetch a blob from an API call and trigger a download.
   * @param {Function} requestFn - Returns a promise resolving to an axios response with blob data
   * @param {string} filename - Suggested download filename
   */
  async function downloadFromApi(requestFn, filename) {
    const response = await requestFn()
    downloadBlob(response.data, filename)
  }

  return { downloadBlob, downloadFromApi }
}
