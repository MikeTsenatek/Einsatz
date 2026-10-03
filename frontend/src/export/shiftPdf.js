import { jsPDF } from 'jspdf'
import { autoTable } from 'jspdf-autotable'

const dateTime = new Intl.DateTimeFormat('de-DE', { timeZone: 'Europe/Berlin', dateStyle: 'short', timeStyle: 'short' })
export const formatTimestamp = value => value === null || value === undefined || value === '' ? '–' : dateTime.format(new Date(value))
const birthday = value => value ? value.split('-').reverse().join('.') : '–'
export function formatDuration(ms) {
  const minutes = Math.floor(ms / 60000)
  return `${Math.floor(minutes / 60)} Std. ${minutes % 60} Min.`
}
export async function createShiftPdf(report, { fontData } = {}) {
  if (!fontData) {
    const response = await fetch('/fonts/DejaVuSans.ttf')
    if (!response.ok) throw new Error('Die PDF-Schrift konnte nicht geladen werden.')
    fontData = new Uint8Array(await response.arrayBuffer())
  }
  let font = ''
  for (let i = 0; i < fontData.length; i += 8192) font += String.fromCharCode(...fontData.subarray(i, i + 8192))
  const doc = new jsPDF({ orientation: 'landscape', format: 'a4', compress: true, putOnlyUsedFonts: true })
  doc.addFileToVFS('DejaVuSans.ttf', btoa(font))
  doc.addFont('DejaVuSans.ttf', 'DejaVu', 'normal')
  doc.setFont('DejaVu', 'normal')
  doc.setProperties({ title: `Schichtexport – ${report.mission.name}`, subject: 'Einsatzbericht', creator: 'EinSatz' })
  const width = doc.internal.pageSize.getWidth()
  const height = doc.internal.pageSize.getHeight()
  const heading = title => {
    doc.setTextColor(8, 29, 46)
    doc.setFontSize(17)
    doc.text(title, 14, 22)
  }
  const table = (head, body, options = {}) => autoTable(doc, {
    startY: 32, margin: { top: 32, bottom: 18, left: 14, right: 14 },
    head: [head], body,
    theme: 'striped', showHead: 'everyPage', rowPageBreak: 'avoid',
    styles: { font: 'DejaVu', fontStyle: 'normal', fontSize: 8, cellPadding: 2.5, overflow: 'linebreak' },
    headStyles: { fillColor: [8, 29, 46], fontStyle: 'normal' },
    ...options,
  })
  const empty = text => { doc.setFontSize(11); doc.text(text, 14, 40) }
  heading('1) Übersicht und Einsatzzahlen')
  const s = report.summary
  table(['Angabe', 'Wert'], [
    ['Einsatz', report.mission.name],
    ['Export', report.fullMission ? 'Kompletter Einsatz' : 'Schicht / Zeitraum'],
    ['Von', formatTimestamp(report.from)], ['Bis', formatTimestamp(report.to)],
    ['Dauer des Zeitraums', formatDuration(report.to - report.from)],
    ['Erstellt', formatTimestamp(report.generatedAt) + ' (Europe/Berlin)'],
    ['Behandlungen im Zeitraum / davon neu begonnen', `${s.treatments} / ${s.newTreatments}`],
    ['Abgeschlossene Behandlungen / Abtransporte durch ö.r. Rettungsdienst', `${s.completedTreatments} / ${s.transports}`],
    ['Patienten / Behandlungen ohne Patientenzuordnung', `${s.patients} / ${s.unassigned}`],
    ['ETB-Einträge / gestrichene Einträge', `${s.entries} / ${s.struckEntries}`],
    ['Helfer / besetzte Teams / Dienstzeiten', `${s.helpers} / ${s.teams} / ${report.assignments.length}`],
    ['Helferstunden im Zeitraum (pro Helfer ohne doppelte Zeiten)', formatDuration(s.helperDuration)],
  ], { columnStyles: { 0: { cellWidth: 155 } } })
  let y = doc.lastAutoTable.finalY + 8
  const note = 'Zeiten: Europe/Berlin. Zeitraum: Von einschließlich, Bis ausschließlich. Behandlungen und Dienste werden bei zeitlicher Überschneidung berücksichtigt. Laufende Helferdienste zählen bis zur Erstellung. Patienten erscheinen pro Behandlung. ETB enthält auch gekennzeichnete gestrichene Einträge.'
  doc.setFontSize(9)
  const lines = doc.splitTextToSize(note, width - 28)
  if (y + lines.length * 4 > height - 18) { doc.addPage(); y = 36 }
  doc.setFontSize(9); doc.text(lines, 14, y)

  doc.addPage(); heading('2) Patienten und Behandlungen')
  if (!report.treatments.length) empty('Keine Behandlungen im ausgewählten Zeitraum.')
  else table(['Nr.', 'Name', 'Geburtsdatum', 'Beginn', 'Ende', 'Entlassungsort', 'Stichwort'], report.treatments.map(t => [
    String(t.number ?? t.id), t.patient?.name || t.patient?.display_name || 'Ohne Patientenzuordnung', birthday(t.patient?.birthday),
    formatTimestamp(t.start_date), t.end_date ? formatTimestamp(t.end_date) : 'Laufend', t.discharge_destination || '–', t.keyword || '–',
  ]), { columnStyles: { 0: { cellWidth: 13 }, 2: { cellWidth: 26 }, 3: { cellWidth: 31 }, 4: { cellWidth: 31 } } })

  doc.addPage(); heading('3) Einsatztagebuch (ETB)')
  if (!report.entries.length) empty('Keine ETB-Einträge im ausgewählten Zeitraum.')
  else table(['Nr. / Status', 'Zeitpunkt', 'Von / An', 'Priorität', 'Meldung', 'Maßnahme'], report.entries.map(e => [
    `${e.number ?? e.id}${e.is_struck_out ? '\nGESTRICHEN' : ''}`, formatTimestamp(e.timestamp), `${e.sender || '–'}\n→ ${e.recipient || '–'}`,
    `${e.priority_level ?? ''} ${e.priority_name || ''}`.trim(), e.text, e.measure || '–',
  ]), { columnStyles: { 0: { cellWidth: 24 }, 1: { cellWidth: 31 }, 2: { cellWidth: 38 }, 3: { cellWidth: 28 } },
    didParseCell: data => {
      if (data.section === 'body' && report.entries[data.row.index]?.is_struck_out) data.cell.styles.textColor = [145, 65, 60]
    },
  })

  doc.addPage(); heading('4) Helfer – sortiert nach Gliederung')
  if (!report.assignments.length) empty('Keine Helferdienste im ausgewählten Zeitraum.')
  else table(['Gliederung / HiOrg - Kreisverband - Gemeinschaft', 'Name / Geburtstag', 'Team', 'Dienstbeginn', 'Dienstende', 'Zeit im Export'], report.assignments.map(a => [
    a.helper.hiorg ? `${a.helper.hiorg.gliederung || 'Ohne Gliederung'}\n${a.helper.hiorg.hiorg} - ${a.helper.hiorg.kreisverband} - ${a.helper.hiorg.gemeinschaft}` : 'Ohne HiOrg / Gliederung',
    `${a.helper.name}\n${birthday(a.helper.birthday)}`, a.team?.name || '–', formatTimestamp(a.start_date),
    a.end_date || a.team?.end_date ? formatTimestamp(Math.min(...[a.end_date, a.team?.end_date].filter(Boolean).map(Date.parse))) : 'Laufend',
    formatDuration(a.duration),
  ]), { columnStyles: { 0: { cellWidth: 77 }, 1: { cellWidth: 48 }, 3: { cellWidth: 31 }, 4: { cellWidth: 31 }, 5: { cellWidth: 30 } } })

  const total = doc.getNumberOfPages()
  for (let page = 1; page <= total; page++) {
    doc.setPage(page); doc.setFontSize(8); doc.setTextColor(100)
    const name = doc.splitTextToSize(`EinSatz · ${report.mission.name}`, width - 75)[0]
    doc.text(name, 14, 9)
    doc.text('Schichtexport · Europe/Berlin', 14, height - 8)
    doc.text(`Seite ${page} / ${total}`, width - 14, height - 8, { align: 'right' })
  }
  return doc
}
export function shiftFilename(report) {
  const name = report.mission.name.replace(/[^\p{L}\p{N} _-]/gu, '').trim().replace(/\s+/g, '_') || 'Einsatz'
  return `Schichtexport_${name}_${report.fullMission ? 'gesamt' : new Date(report.from).toISOString().slice(0, 16).replace(/[:T]/g, '-')}.pdf`
}
