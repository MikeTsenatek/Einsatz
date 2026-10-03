import { test } from 'node:test'
import assert from 'node:assert/strict'
import { berlinTimestamp, buildShiftReport, loadAll } from './shiftData.js'
const t = value => Date.parse(`2026-10-03T${value}:00Z`)
const mission = { id: 1, name: 'Testeinsatz' }
const helper = (id, name, gliederung) => ({ id, name, hiorg: gliederung ? { gliederung, hiorg: 'BRK', kreisverband: 'Test', gemeinschaft: 'Bereitschaft' } : null })

test('Schichtgrenzen, laufende Behandlungen, Abschlusszahlen und ETB', () => {
  const report = buildShiftReport({ mission, from: t('08:00'), to: t('16:00'), now: t('18:00'), assignments: [],
    treatments: [
      { id: 1, patient: { id: 1 }, start_date: new Date(t('07:00')).toISOString(), end_date: new Date(t('09:00')).toISOString(), transported_by_public_ems: true },
      { id: 2, patient: { id: 1 }, start_date: new Date(t('09:00')).toISOString(), end_date: null },
      { id: 3, start_date: new Date(t('06:00')).toISOString(), end_date: new Date(t('08:00')).toISOString() },
      { id: 4, start_date: new Date(t('16:00')).toISOString() },
    ], entries: [
      { id: 1, timestamp: new Date(t('08:00')).toISOString() },
      { id: 2, timestamp: new Date(t('09:00')).toISOString(), is_struck_out: true },
      { id: 3, timestamp: new Date(t('16:00')).toISOString() },
    ],
  })
  assert.deepEqual(report.treatments.map(t => t.id), [1, 2])
  assert.equal(report.summary.newTreatments, 1)
  assert.equal(report.summary.completedTreatments, 1)
  assert.equal(report.summary.transports, 1)
  assert.equal(report.summary.patients, 1)
  assert.equal(report.summary.entries, 1)
  assert.equal(report.summary.struckEntries, 1)
})

test('Gliederungssortierung, Teamende und Helferstunden ohne Doppelzählung', () => {
  const assignment = (id, person, start, end, team = null) => ({ id, helper: person, start_date: new Date(t(start)).toISOString(), end_date: end && new Date(t(end)).toISOString(), team })
  const person = helper(1, 'Änne', 'Z-Ort')
  const report = buildShiftReport({ mission, from: t('08:00'), to: t('16:00'), now: t('15:00'), treatments: [], entries: [], assignments: [
    assignment(1, person, '07:00', '12:00'), assignment(2, person, '10:00', null),
    assignment(3, helper(2, 'Bert', 'A-Ort'), '08:00', null, { id: 1, end_date: new Date(t('10:00')).toISOString() }),
    assignment(4, helper(3, 'Clara'), '08:00', '09:00'),
  ] })
  assert.deepEqual(report.assignments.map(a => a.id), [3, 1, 2, 4])
  assert.equal(report.summary.helperDuration, 10 * 3600000)
  assert.equal(report.summary.helpers, 3)
  assert.equal(report.assignments[0].duration, 2 * 3600000)
})

test('Gesamter Einsatz und leerer Einsatz sind exportierbar; falsche Grenzen werden abgewiesen', () => {
  const report = buildShiftReport({ mission, treatments: [], entries: [], assignments: [], now: t('18:00') })
  assert.equal(report.fullMission, true)
  assert.equal(report.summary.helpers, 0)
  assert.throws(() => buildShiftReport({ mission, treatments: [], entries: [], assignments: [], from: t('16:00'), to: t('08:00') }))
})

test('Berlin-Zeiten und Zeitumstellung werden unabhängig von Browserzeitzone geprüft', () => {
  assert.equal(berlinTimestamp('2026-10-03T10:00'), t('08:00'))
  assert.equal(berlinTimestamp('2026-12-01T10:00'), Date.parse('2026-12-01T09:00Z'))
  assert.throws(() => berlinTimestamp('2026-03-29T02:30'))
  assert.throws(() => berlinTimestamp('2026-10-25T02:30'))
})

test('Alle API-Seiten werden geladen; fremde Folgeseiten werden abgewiesen', async () => {
  globalThis.window = { location: { origin: 'https://einsatz.test' } }
  const calls = []
  const api = async path => { calls.push(path); return calls.length === 1 ? { results: [{ id: 1 }], next: 'https://einsatz.test/api/missions/1/treatments/?page=2' } : { results: [{ id: 2 }], next: null } }
  assert.deepEqual(await loadAll(api, '/missions/1/treatments/'), [{ id: 1 }, { id: 2 }])
  assert.equal(calls.length, 2)
  await assert.rejects(loadAll(async () => ({ results: [], next: 'https://other.test/api/missions/1/treatments/' }), '/missions/1/treatments/'))
})
