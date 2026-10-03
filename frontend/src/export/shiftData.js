export const exportPermissions = [
  ['missions.view_mission', 'Einsatz'],
  ['patients.view_treatment', 'Behandlungen'],
  ['patients.view_patient', 'Patienten'],
  ['missions.view_operationlogentry', 'Einsatztagebuch'],
  ['teams.view_helpermission', 'Helferdienste'],
  ['teams.view_team', 'Teams'],
]
const berlinParts = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Berlin', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
export function berlinInput(date = new Date()) {
  return berlinParts.format(date).replace(' ', 'T')
}
export function berlinTimestamp(value) {
  const guess = Date.parse(value + 'Z')
  if (!Number.isFinite(guess)) throw new Error('Bitte gültige Zeiten eingeben.')
  const matches = []
  for (let offset = -180; offset <= 180; offset += 30) {
    const candidate = guess + offset * 60000
    if (berlinInput(candidate) === value) matches.push(candidate)
  }
  if (matches.length !== 1) throw new Error('Diese Uhrzeit ist wegen der Zeitumstellung nicht eindeutig oder existiert nicht. Bitte eine andere Uhrzeit wählen.')
  return matches[0]
}
const stamp = value => value ? Date.parse(value) : null
const chronological = (a, b) => stamp(a.start_date || a.timestamp) - stamp(b.start_date || b.timestamp) || a.id - b.id
export function dutyEnd(item) {
  const ends = [stamp(item.end_date), stamp(item.team?.end_date)].filter(value => value !== null)
  return ends.length ? Math.min(...ends) : null
}
function overlaps(start, end, from, to) {
  return start < to && (end === null || end > from || (end === start && start >= from))
}
export function mergedDuration(intervals) {
  const ordered = intervals.slice().sort((a, b) => a[0] - b[0])
  let total = 0, previous = null
  for (const [start, end] of ordered) {
    if (end <= start) continue
    if (previous && start <= previous[1]) previous[1] = Math.max(previous[1], end)
    else { if (previous) total += previous[1] - previous[0]; previous = [start, end] }
  }
  return total + (previous ? previous[1] - previous[0] : 0)
}
export function buildShiftReport({ mission, treatments, entries, assignments, from = null, to = null, now = Date.now() }) {
  if ((from === null) !== (to === null) || (from !== null && (!Number.isFinite(from) || !Number.isFinite(to) || from >= to))) throw new Error('Das Ende muss nach dem Beginn liegen.')
  const fullMission = from === null
  const timestamps = [...treatments.flatMap(t => [stamp(t.start_date), stamp(t.end_date)]), ...entries.map(e => stamp(e.timestamp)), ...assignments.flatMap(a => [stamp(a.start_date), dutyEnd(a)])].filter(Number.isFinite)
  const rangeFrom = fullMission ? (timestamps.length ? timestamps.reduce((min, value) => Math.min(min, value), Infinity) : now) : from
  const rangeTo = fullMission ? timestamps.reduce((max, value) => Math.max(max, value), now) + 1 : to
  const includedTreatments = treatments.filter(t => fullMission || overlaps(stamp(t.start_date), stamp(t.end_date), from, to)).sort(chronological)
  const includedEntries = entries.filter(e => fullMission || (stamp(e.timestamp) >= from && stamp(e.timestamp) < to)).sort(chronological)
  const collator = new Intl.Collator('de', { numeric: true, sensitivity: 'base' })
  const includedAssignments = assignments.filter(a => fullMission || overlaps(stamp(a.start_date), dutyEnd(a), from, to)).map(a => {
    const start = Math.max(stamp(a.start_date), rangeFrom)
    const end = Math.max(start, Math.min(dutyEnd(a) ?? now, rangeTo, now))
    return { ...a, exportStart: start, exportEnd: end, duration: end - start }
  }).sort((a, b) => {
    for (const field of ['gliederung', 'hiorg', 'kreisverband', 'gemeinschaft']) {
      const result = collator.compare(a.helper.hiorg?.[field] || '\uffff', b.helper.hiorg?.[field] || '\uffff')
      if (result) return result
    }
    return collator.compare(a.helper.name, b.helper.name) || chronological(a, b)
  })
  const intervals = new Map()
  for (const a of includedAssignments) {
    if (!intervals.has(a.helper.id)) intervals.set(a.helper.id, [])
    intervals.get(a.helper.id).push([a.exportStart, a.exportEnd])
  }
  const inRange = value => fullMission || (stamp(value) >= from && stamp(value) < to)
  return {
    mission, fullMission, from: rangeFrom, to: fullMission ? rangeTo - 1 : rangeTo, generatedAt: now,
    treatments: includedTreatments, entries: includedEntries, assignments: includedAssignments,
    summary: {
      treatments: includedTreatments.length,
      newTreatments: includedTreatments.filter(t => inRange(t.start_date)).length,
      completedTreatments: includedTreatments.filter(t => t.end_date && inRange(t.end_date)).length,
      patients: new Set(includedTreatments.filter(t => t.patient).map(t => t.patient.id)).size,
      unassigned: includedTreatments.filter(t => !t.patient).length,
      transports: includedTreatments.filter(t => t.transported_by_public_ems && t.end_date && inRange(t.end_date)).length,
      entries: includedEntries.filter(e => !e.is_struck_out).length,
      struckEntries: includedEntries.filter(e => e.is_struck_out).length,
      helpers: intervals.size,
      teams: new Set(includedAssignments.filter(a => a.team).map(a => a.team.id)).size,
      helperDuration: [...intervals.values()].reduce((sum, rows) => sum + mergedDuration(rows), 0),
    },
  }
}
// Follow every page: treatments and ETB use paginated API responses.
export async function loadAll(api, path, options = {}) {
  const rows = []
  let page = path
  const visited = new Set()
  while (page) {
    if (visited.has(page)) throw new Error('Die Daten konnten nicht vollständig geladen werden.')
    visited.add(page)
    const data = await api(page, options)
    if (Array.isArray(data)) { rows.push(...data); break }
    if (!Array.isArray(data.results)) throw new Error('Unerwartete Antwort beim Laden der Exportdaten.')
    rows.push(...data.results)
    if (!data.next) break
    const next = new URL(data.next, window.location.origin)
    if (next.origin !== window.location.origin || next.pathname !== '/api' + path.split('?')[0]) throw new Error('Ungültige Folgeseite beim Laden der Exportdaten.')
    page = next.pathname.slice(4) + next.search
  }
  return rows
}
