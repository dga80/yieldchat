/**
 * Utilidades para clasificación y formateo temporal de sesiones en YieldChat
 */

const MONTHS_FULL = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

const MONTHS_SHORT = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
]

/**
 * Determina la categoría temporal de una sesión según su fecha (updated_at o created_at)
 */
export function categorizeSessionByDate(dateStr) {
  if (!dateStr) return 'Anteriores'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return 'Anteriores'

  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const sessionDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())

  const diffDays = Math.round((today - sessionDay) / (1000 * 60 * 60 * 24))

  if (diffDays <= 0) return 'Hoy'
  if (diffDays === 1) return 'Ayer'
  if (diffDays <= 7) return 'Últimos 7 días'
  if (diffDays <= 30) return 'Últimos 30 días'

  // Si es del mismo año actual, agrupar por nombre de mes
  if (date.getFullYear() === now.getFullYear()) {
    return MONTHS_FULL[date.getMonth()]
  }

  // Años anteriores
  return `${MONTHS_FULL[date.getMonth()]} ${date.getFullYear()}`
}

/**
 * Formatea una fecha de sesión para mostrarla legiblemente (ej: "Hoy, 11:32", "9 Sep, 20:15")
 */
export function formatSessionDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return ''

  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()

  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  const isYesterday = d.toDateString() === yesterday.toDateString()

  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const timeStr = `${hours}:${minutes}`

  if (isToday) return `Hoy, ${timeStr}`
  if (isYesterday) return `Ayer, ${timeStr}`

  if (d.getFullYear() === now.getFullYear()) {
    return `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}, ${timeStr}`
  }

  return `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()}`
}

/**
 * Agrupa una lista de sesiones en bloques cronológicos ordenados de más reciente a más antiguo
 */
export function groupSessionsByDate(sessions = []) {
  if (!sessions || sessions.length === 0) return []

  // 1. Ordenar sesiones por última actividad descendente
  const sorted = [...sessions].sort((a, b) => {
    const timeA = new Date(a.updated_at || a.created_at || 0).getTime()
    const timeB = new Date(b.updated_at || b.created_at || 0).getTime()
    return timeB - timeA
  })

  // 2. Agrupar preservando el orden cronológico natural
  const groups = []
  const groupMap = new Map()

  for (const session of sorted) {
    const category = categorizeSessionByDate(session.updated_at || session.created_at)
    if (!groupMap.has(category)) {
      const groupObj = { category, sessions: [] }
      groupMap.set(category, groupObj)
      groups.push(groupObj)
    }
    groupMap.get(category).sessions.push(session)
  }

  return groups
}
