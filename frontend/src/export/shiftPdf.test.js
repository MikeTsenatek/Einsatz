import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { buildShiftReport } from './shiftData.js'
import { createShiftPdf, shiftFilename } from './shiftPdf.js'
const fontData = new Uint8Array(await readFile(new URL('../../public/fonts/DejaVuSans.ttf', import.meta.url)))
const mission = { id: 1, name: 'Übung München / Süd' }
const start_date = '2026-10-03T08:00:00Z'

test('Leerer Einsatz erzeugt vier PDF-Abschnitte mit sicherem Dateinamen', async () => {
  const report = buildShiftReport({ mission, treatments: [], entries: [], assignments: [], now: Date.parse(start_date) })
  const doc = await createShiftPdf(report, { fontData })
  assert.equal(doc.getNumberOfPages(), 4)
  assert.equal(doc.output().slice(0, 8), '%PDF-1.3')
  assert.equal(shiftFilename(report), 'Schichtexport_Übung_München_Süd_gesamt.pdf')
})

test('Lange Tabellen und ETB-Meldungen erzeugen zusätzliche PDF-Seiten', async () => {
  const report = buildShiftReport({ mission, assignments: [], treatments: Array.from({ length: 70 }, (_, i) => ({
    id: i + 1, number: i + 1, start_date,
    patient: { id: i + 1, name: `Jörg Müller ${i}`, birthday: '1990-05-10' },
    keyword: 'Kreislaufbeschwerden', discharge_destination: 'Klinikum München',
  })), entries: Array.from({ length: 35 }, (_, i) => ({
    id: i + 1, timestamp: start_date, sender: 'Einsatzleitung', recipient: 'Ärztin',
    text: 'Längere Meldung mit Umlauten: Ä Ö Ü ß. '.repeat(20), measure: 'Maßnahme dokumentiert', is_struck_out: i === 0,
  })) })
  const doc = await createShiftPdf(report, { fontData })
  assert.ok(doc.getNumberOfPages() > 4)
  assert.ok(doc.output('arraybuffer').byteLength > 10000)
})
