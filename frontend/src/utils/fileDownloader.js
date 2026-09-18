import toast from 'react-hot-toast'

/**
 * Descarga una cadena de texto como archivo en el navegador del usuario.
 * @param {string} filename Nombre del archivo (ej. 'guion_completo.txt')
 * @param {string} content Contenido de texto a descargar
 */
export function downloadTextAsFile(filename, content) {
  if (!content) {
    toast.error('No hay contenido para descargar')
    return
  }

  let cleanName = (filename || 'yieldchat_documento.txt').trim()
  if (!cleanName.includes('.')) {
    cleanName += '.txt'
  }

  try {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = cleanName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    toast.success(`Descargado: ${cleanName}`, { icon: '📄' })
  } catch (err) {
    console.error('Error al descargar archivo:', err)
    toast.error('No se pudo descargar el archivo')
  }
}
