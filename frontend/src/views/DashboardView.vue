<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { api } from '../api'

const props = defineProps({ user: Object, mission: { type: Object, required: true } })
const emit = defineEmits(['navigate'])
const now = ref(new Date())
const loading = ref(false)
const patients = ref(null)
const helpers = ref(null)
const log = ref(null)
const errors = ref([])
const updatedAt = ref(null)
let controller

const time = computed(() => now.value.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }))
const activeHelpers = computed(() => helpers.value?.filter((item) => !item.end_date) ?? [])
const activeTeams = computed(() => new Set(activeHelpers.value.map((item) => item.team?.id).filter((id) => id != null)).size)
const recentEntries = computed(() => log.value?.results.slice(0, 5) ?? [])

function formatDate(value) {
  return new Date(value).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function load() {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  const missionId = props.mission.id
  const sources = [
    { label: 'Patienten', target: patients, path: `/patients/?mission=${missionId}` },
    { label: 'Helfer und Teams', target: helpers, path: `/missions/${missionId}/helpers/` },
    { label: 'Einsatztagebuch', target: log, path: `/missions/${missionId}/operation-log/?visibility=active` },
  ]
  const results = await Promise.allSettled(sources.map((source) => api(source.path, { signal: request.signal })))
  if (request.signal.aborted) return
  errors.value = []
  results.forEach((result, index) => {
    const source = sources[index]
    if (result.status === 'fulfilled') {
      source.target.value = result.value
    } else {
      source.target.value = null
      errors.value.push(`${source.label}: ${result.reason?.message || 'Daten konnten nicht geladen werden.'}`)
    }
  })
  updatedAt.value = new Date()
  loading.value = false
}

watch(() => props.mission.id, () => {
  patients.value = null
  helpers.value = null
  log.value = null
  errors.value = []
  updatedAt.value = null
  load()
}, { immediate: true })

const timer = window.setInterval(() => {
  now.value = new Date()
  if (!loading.value && !document.hidden) load()
}, 30000)

onBeforeUnmount(() => {
  window.clearInterval(timer)
  controller?.abort()
})
</script>

<template>
  <div class="dashboard">
    <section class="welcome">
      <div>
        <p class="overline red">Lagezentrum</p><h1>Guten Tag, {{ user?.name }}.</h1>
        <p class="muted">Aktuelle Übersicht für {{ mission.name }}.</p>
      </div>
      <strong>{{ time }} <small>Uhr</small></strong>
    </section>
    <div class="dashboard-toolbar">
      <span role="status">{{ loading ? 'Daten werden geladen …' : updatedAt ? `Letzte Abfrage: ${formatDate(updatedAt)}` : 'Daten werden vorbereitet …' }}</span>
      <button class="secondary" :disabled="loading" @click="load">Aktualisieren</button>
    </div>
    <div v-if="errors.length" class="error" role="alert">
      <p v-for="error in errors" :key="error">{{ error }}</p>
    </div>
    <section class="stats" aria-label="Kennzahlen" :aria-busy="loading">
      <article>
        <span>Patienten</span><b>{{ patients === null ? '–' : patients.length }}</b>
        <small>{{ patients === null ? 'Keine Daten verfügbar' : 'Im Einsatz erfasst' }}</small>
        <button class="dashboard-link" @click="emit('navigate', 'patients')">Patienten öffnen →</button>
      </article>
      <article>
        <span>Aktive Teams</span><b>{{ helpers === null ? '–' : activeTeams }}</b>
        <small>{{ helpers === null ? 'Keine Daten verfügbar' : `${activeHelpers.length} Helfer im Dienst · Teams mit Helfern im Dienst` }}</small>
        <button class="dashboard-link" @click="emit('navigate', 'teams')">Helfer öffnen →</button>
      </article>
      <article>
        <span>Tagebucheinträge</span><b>{{ log === null ? '–' : log.count }}</b>
        <small>{{ log === null ? 'Keine Daten verfügbar' : 'Nicht gestrichene Einträge' }}</small>
        <button class="dashboard-link" @click="emit('navigate', 'operationLog')">Einsatztagebuch öffnen →</button>
      </article>
    </section>
    <section class="activity" :aria-busy="loading">
      <div class="activity-heading">
        <h2>Letzte Tagebucheinträge</h2>
        <button class="dashboard-link" @click="emit('navigate', 'operationLog')">Alle anzeigen →</button>
      </div>
      <p v-if="log === null" class="activity-empty">{{ loading ? 'Einträge werden geladen …' : 'Einträge konnten nicht geladen werden.' }}</p>
      <p v-else-if="!recentEntries.length" class="activity-empty">Noch keine nicht gestrichenen Tagebucheinträge vorhanden.</p>
      <ol v-else class="recent-entries">
        <li v-for="entry in recentEntries" :key="entry.id">
          <div class="entry-meta">
            <time :datetime="entry.timestamp">{{ formatDate(entry.timestamp) }}</time>
            <span v-if="entry.priority_name" class="priority" :class="`priority--${entry.priority_level}`">{{ entry.priority_name }}</span>
          </div>
          <div v-if="entry.sender || entry.recipient" class="entry-route">{{ entry.sender || '–' }} → {{ entry.recipient || '–' }}</div>
          <p class="entry-text">{{ entry.text }}</p>
        </li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.dashboard-toolbar, .activity-heading, .entry-meta { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.dashboard-toolbar { margin-top: 20px; color: #596570; font-size: 13px; }
.dashboard-toolbar button { padding: 9px 12px; }
.stats article { display: flex; flex-direction: column; align-items: flex-start; }
.stats small { margin-bottom: 18px; line-height: 1.5; }
.dashboard-link { border: 0; padding: 4px 0; background: none; color: #315a70; font-size: 13px; text-align: left; }
.dashboard-link:hover { text-decoration: underline; }
.stats .dashboard-link { margin-top: auto; }
.activity-heading h2 { margin: 0; font-size: 19px; }
.recent-entries { padding: 0; margin: 20px 0 0; list-style: none; }
.recent-entries li { padding: 18px 0; border-top: 1px solid #e3e9ec; }
.recent-entries li:last-child { padding-bottom: 0; }
.entry-meta { justify-content: flex-start; flex-wrap: wrap; color: #596570; font-size: 12px; }
.entry-route { margin-top: 10px; font-size: 13px; color: #50606d; overflow-wrap: anywhere; }
.activity .entry-text { margin: 8px 0 0; padding: 0; border: 0; color: #142535; white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.55; }
.activity .activity-empty { margin: 20px 0 0; color: #596570; }
.error p { margin: 0; }
.error p + p { margin-top: 8px; }
@media (max-width: 480px) {
  .dashboard-toolbar, .activity-heading { align-items: flex-start; flex-direction: column; gap: 8px; }
}
</style>
