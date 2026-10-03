<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { api } from '../api'

const props = defineProps({ mission: { type: Object, required: true } })
const data = ref(null)
const loading = ref(false)
const error = ref('')
const from = ref('')
const to = ref('')
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
@media (max-width: 700px) { .statistics-page { padding: 24px 16px; } }
</style>
