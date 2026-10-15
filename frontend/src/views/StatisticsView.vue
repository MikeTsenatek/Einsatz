<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { api } from '../api'

const props = defineProps({ mission: { type: Object, required: true } })
const data = ref(null)
const loading = ref(false)
const error = ref('')
const from = ref('')
const to = ref('')
const zoom = ref(1)
const chartOffset = ref(0)
let controller
const metrics = [
  { key: 'entries', label: 'ETB-Einträge' },
  { key: 'teams', label: 'Trupps' },
  { key: 'treatments', label: 'Behandlungen' },
  { key: 'transports', label: 'Abtransporte' },
  { key: 'helpers', label: 'Helfer' },
]
const columns = computed(() => metrics.filter(item => data.value?.available[item.key]))
const invalidRange = computed(() => from.value && to.value && from.value > to.value)
const rows = computed(() => invalidRange.value ? [] : (data.value?.days ?? []).filter(day =>
  (!from.value || day.date >= from.value) && (!to.value || day.date <= to.value)
).slice().reverse())
const hours = computed(() => invalidRange.value ? [] : (data.value?.hourly ?? []).filter(hour =>
  (!from.value || hour.date >= from.value) && (!to.value || hour.date <= to.value)
))
const windowSize = computed(() => Math.max(1, Math.ceil(hours.value.length / zoom.value)))
const maxOffset = computed(() => Math.max(0, hours.value.length - windowSize.value))
const visibleHours = computed(() => hours.value.slice(chartOffset.value, chartOffset.value + windowSize.value))
const peak = computed(() => visibleHours.value.reduce((maximum, hour) => Math.max(maximum, hour.patients, hour.transports ?? 0), 1))
const ticks = computed(() => [...new Set([0, 1, 2, 3, 4].map(index => Math.round(index * (visibleHours.value.length - 1) / 4)))].filter(index => index >= 0))
watch(hours, () => { zoom.value = 1; chartOffset.value = 0 })
watch(maxOffset, maximum => { chartOffset.value = Math.min(chartOffset.value, maximum) })
function duration(seconds) {
  return (seconds / 3600).toLocaleString('de-DE', { maximumFractionDigits: 2 }) + ' h'
}
function hourLabel(value) {
  return new Date(value).toLocaleString('de-DE', { timeZone: data.value?.timezone || 'Europe/Berlin', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' })
}
function formatDay(value) {
  return new Date(value + 'T12:00:00').toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' })
}
async function load() {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  error.value = ''
  try {
    const result = await api(`/missions/${props.mission.id}/statistics/`, { signal: request.signal })
    if (!request.signal.aborted) data.value = result
  } catch (failure) {
    if (!request.signal.aborted) {
      data.value = null
      error.value = failure.message
    }
  } finally {
    if (!request.signal.aborted) loading.value = false
  }
}
watch(() => props.mission.id, () => {
  data.value = null
  from.value = ''
  to.value = ''
  load()
}, { immediate: true })
onBeforeUnmount(() => controller?.abort())
</script>

<template>
  <div class="statistics-page">
    <section class="welcome">
      <div><h1>Statistik</h1><p class="muted">Tagesübersicht für {{ mission.name }}</p></div>
      <button class="secondary" :disabled="loading" @click="load">Aktualisieren</button>
    </section>
    <div class="statistics-filters">
      <label>Von<input v-model="from" type="date" :max="to || undefined"></label>
      <label>Bis<input v-model="to" type="date" :min="from || undefined"></label>
      <button v-if="from || to" class="secondary" @click="from = ''; to = ''">Zeitraum zurücksetzen</button>
    </div>
    <p v-if="invalidRange" class="error" role="alert">Das Enddatum muss am oder nach dem Anfangsdatum liegen.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="loading" role="status">Statistik wird geladen …</p>
    <template v-else-if="data">
      <section v-if="data.summary" class="statistics-summary" aria-label="Gesamter Einsatz">
        <article v-if="data.summary.treatment_seconds !== null"><span>Gesamte Behandlungszeit</span><strong>{{ duration(data.summary.treatment_seconds) }}</strong></article>
        <article v-if="data.summary.helper_seconds !== null"><span>Gesamte Dienstzeit aller Helfer</span><strong>{{ duration(data.summary.helper_seconds) }}</strong></article>
        <article v-if="data.summary.known_age_count !== null"><span>Durchschnittsalter der Patienten</span><strong>{{ data.summary.average_age === null ? 'Keine Altersangaben' : data.summary.average_age.toLocaleString('de-DE', { maximumFractionDigits: 1 }) + ' Jahre' }}</strong><small>{{ data.summary.known_age_count }} mit bekanntem Alter</small></article>
      </section>
      <p v-if="data.summary" class="muted">Kennzahlen für den gesamten Einsatz. Laufende Zeiten zählen bis zum Abruf; überlappende Dienste desselben Helfers werden einmal gezählt.</p>
      <section v-if="data.available.treatments" class="occupancy">
        <h2>Patientenbelegung und Abtransporte</h2>
        <p class="muted">Durchschnittliche Belegung je Stunde im ausgewählten Zeitraum. 30 Minuten Behandlung entsprechen 0,5 Patienten. Mehrere gleichzeitige Behandlungen desselben Patienten zählen einmal; ohne Zuordnung zählt jede Behandlung separat. Abtransporte werden je Stunde anhand der Endzeit der abgeschlossenen Behandlung gezählt.</p>
        <div v-if="hours.length" class="chart-panel">
          <div class="chart-controls">
            <label>Zoom
              <select v-model.number="zoom">
                <option :value="1">Gesamter Zeitraum</option>
                <option :value="2">2×</option>
                <option :value="4">4×</option>
                <option :value="8">8×</option>
              </select>
            </label>
            <span class="muted">{{ visibleHours.length }} von {{ hours.length }} Stunden</span>
            <button v-if="zoom > 1" class="secondary" @click="zoom = 1; chartOffset = 0">Übersicht</button>
          </div>
          <div class="chart-legend">
            <span><i class="legend-patients"></i>Patienten gleichzeitig (Ø je Stunde)</span>
            <span><i class="legend-transports"></i>Abtransporte (Anzahl je Stunde)</span>
          </div>
          <div class="chart-plot">
            <div class="chart-y-axis" aria-hidden="true"><span>{{ peak.toLocaleString('de-DE', { maximumFractionDigits: 1 }) }}</span><span>0</span></div>
            <svg class="hour-chart" viewBox="0 0 1000 180" preserveAspectRatio="none" role="img" aria-label="Patientenbelegung und Abtransporte je Stunde; türkise Balken zeigen die durchschnittliche Belegung, orange Balken die Abtransporte">
              <line x1="0" y1="179" x2="1000" y2="179" stroke="#adb5bd" />
              <rect v-for="(hour, index) in visibleHours" :key="hour.start"
                :x="index * 1000 / visibleHours.length"
                :y="179 - hour.patients / peak * 175"
                :width="Math.max(0.1, 1000 / visibleHours.length * 0.4)"
                :height="hour.patients / peak * 175"
                class="hour-bar" tabindex="0" :aria-label="hourLabel(hour.start) + ': ' + hour.patients.toLocaleString('de-DE') + ' Patienten'">
                <title>{{ hourLabel(hour.start) }}: {{ hour.patients.toLocaleString('de-DE') }} Patienten</title>
              </rect>
              <rect v-for="(hour, index) in visibleHours" :key="'transport-' + hour.start"
                :x="(index + 0.45) * 1000 / visibleHours.length"
                :y="179 - (hour.transports ?? 0) / peak * 175"
                :width="Math.max(0.1, 1000 / visibleHours.length * 0.4)"
                :height="(hour.transports ?? 0) / peak * 175"
                class="transport-bar" tabindex="0" :aria-label="hourLabel(hour.start) + ': ' + (hour.transports ?? 0) + ' Abtransporte'">
                <title>{{ hourLabel(hour.start) }}: {{ hour.transports ?? 0 }} Abtransporte (nach Behandlungsende)</title>
              </rect>
            </svg>
          </div>
          <div class="chart-ticks" aria-hidden="true">
            <small v-for="index in ticks" :key="index">{{ hourLabel(visibleHours[index].start) }}</small>
          </div>
          <label v-if="maxOffset > 0" class="chart-position">Zeitausschnitt verschieben
            <input v-model.number="chartOffset" type="range" min="0" :max="maxOffset" step="1" :aria-valuetext="hourLabel(visibleHours[0].start) + ' bis ' + hourLabel(visibleHours[visibleHours.length - 1].start)">
          </label>
        </div>
        <p v-else class="muted">Keine Behandlungszeiten oder Abtransporte im ausgewählten Zeitraum vorhanden.</p>
      </section>
      <p v-if="!columns.length" class="muted">Für die Statistik fehlen die Leserechte der jeweiligen Bereiche.</p>
      <template v-else>
        <div v-if="rows.length" class="statistics-table-wrap">
          <table class="statistics-table">
            <caption class="sr-only">Anzahl pro Tag im ausgewählten Zeitraum</caption>
            <thead><tr><th scope="col">Tag</th><th v-for="column in columns" :key="column.key" scope="col">{{ column.label }}</th></tr></thead>
            <tbody><tr v-for="day in rows" :key="day.date"><th scope="row">{{ formatDay(day.date) }}</th><td v-for="column in columns" :key="column.key">{{ day[column.key] }}</td></tr></tbody>
          </table>
        </div>
        <p v-else-if="!invalidRange" class="muted">Für diesen Zeitraum sind keine Daten vorhanden.</p>
        <div class="statistics-notes">
          <p>Gezählt wird pro Kalendertag in der Zeitzone Europe/Berlin. Sichtbar sind die Bereiche, für die du Leserechte hast.</p>
          <ul>
            <li v-if="data.available.entries">ETB-Einträge: nach Zeitpunkt des Eintrags, ohne gestrichene Einträge.</li>
            <li v-if="data.available.teams">Trupps: besetzte Trupps, pro Tag einmal gezählt.</li>
            <li v-if="data.available.treatments">Behandlungen: jede Behandlung zählt am Tag ihres Beginns, auch ohne zugeordneten Patienten.</li>
            <li v-if="data.available.transports">Abtransporte: abgeschlossene Behandlungen mit Abtransport durch ö.r. Rettungsdienst, nach Abschlussdatum.</li>
            <li v-if="data.available.helpers">Helfer: jeder Helfer pro Anwesenheitstag einmal, auch bei mehreren Anmeldungen. Laufende Anwesenheiten zählen bis heute.</li>
          </ul>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.statistics-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 24px; }
.statistics-summary article { background: white; border: 1px solid #dce0e3; border-radius: 8px; padding: 20px; display: grid; gap: 10px; }
.statistics-summary strong { font-size: 26px; }
.occupancy { margin: 28px 0; }
.chart-panel { min-width: 0; padding: 16px; background: white; border: 1px solid #dce0e3; border-radius: 8px; }
.chart-controls { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; margin-bottom: 16px; }
.chart-controls label { display: flex; align-items: center; gap: 8px; margin: 0; }
.chart-controls select { padding: 8px; border: 1px solid #dce0e3; border-radius: 6px; background: white; font: inherit; }
.chart-legend { display: flex; flex-wrap: wrap; gap: 12px 24px; margin-bottom: 12px; font-size: 13px; }
.chart-legend span { display: flex; align-items: center; gap: 8px; }
.chart-legend i { width: 12px; height: 12px; border-radius: 2px; }
.legend-patients { background: #237b91; }
.legend-transports { background: #c65c17; }
.transport-bar { fill: #c65c17; }
.transport-bar:hover, .transport-bar:focus { fill: #8d3c0b; stroke: #8d3c0b; outline: none; }
.chart-plot { display: flex; gap: 8px; }
.chart-y-axis { display: flex; flex: 0 0 36px; flex-direction: column; justify-content: space-between; font-size: 12px; text-align: right; }
.hour-chart { display: block; width: 100%; min-width: 0; height: 180px; flex: 1; }
.hour-bar { fill: #237b91; }
.hour-bar:hover, .hour-bar:focus { fill: #145366; stroke: #145366; outline: none; }
.chart-ticks { display: flex; justify-content: space-between; gap: 8px; margin: 8px 0 0 44px; }
.chart-ticks small { flex: 1; min-width: 0; font-size: 11px; overflow-wrap: anywhere; }
.chart-ticks small:last-child { text-align: right; }
.chart-position { display: grid; gap: 8px; margin-top: 16px; font-size: 14px; }
.chart-position input { width: 100%; margin: 0; }
.statistics-page { padding: 42px 4%; }
.statistics-filters { display: flex; gap: 16px; align-items: end; flex-wrap: wrap; margin: 24px 0; }
.statistics-filters label { display: grid; gap: 6px; margin-top: 0; font-size: 14px; }
.statistics-filters input { padding: 10px 12px; border: 1px solid #dce0e3; border-radius: 6px; font: inherit; background: white; }
.statistics-table-wrap { overflow-x: auto; border: 1px solid #dce0e3; border-radius: 8px; background: white; }
.statistics-table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
.statistics-table th, .statistics-table td { padding: 14px 18px; border-bottom: 1px solid #e8ebed; text-align: right; white-space: nowrap; }
.statistics-table th:first-child { text-align: left; }
.statistics-table thead { background: #f5f6f7; }
.statistics-table tbody th { font-weight: 500; }
.statistics-table tbody tr:last-child > * { border-bottom: 0; }
.statistics-notes { margin-top: 24px; color: #596570; font-size: 14px; line-height: 1.6; }
@media (max-width: 700px) {
  .statistics-page { padding: 24px 16px; }
  .chart-panel { padding: 12px; }
  .chart-ticks small:nth-child(2), .chart-ticks small:nth-child(4) { display: none; }
}
</style>
