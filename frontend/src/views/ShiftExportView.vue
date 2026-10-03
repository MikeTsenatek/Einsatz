<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { api } from '../api'
import { hasPermission } from '../permissions'
import { berlinInput, berlinTimestamp, buildShiftReport, exportPermissions, loadAll } from '../export/shiftData'

const props = defineProps({ mission: { type: Object, required: true }, user: Object })
const mode = ref('all')
const from = ref(berlinInput(new Date(Date.now() - 8 * 3600000)))
const to = ref(berlinInput())
const busy = ref(false)
const error = ref('')
const status = ref('')
const missing = computed(() => exportPermissions.filter(([permission]) => !hasPermission(props.user, permission)).map(([, label]) => label))
let controller
watch(() => props.mission.id, () => {
  controller?.abort()
  busy.value = false
  error.value = ''
  status.value = ''
  mode.value = 'all'
})
onBeforeUnmount(() => controller?.abort())
async function exportPdf() {
  if (busy.value || missing.value.length) return
  error.value = ''
  status.value = ''
  const request = new AbortController()
  controller = request
  const mission = { ...props.mission }
  busy.value = true
  try {
    const bounds = mode.value === 'range' ? { from: berlinTimestamp(from.value), to: berlinTimestamp(to.value) } : {}
    if (mode.value === 'range' && bounds.from >= bounds.to) throw new Error('Das Ende muss nach dem Beginn liegen.')
    status.value = 'Einsatzdaten werden vollständig geladen …'
    const base = `/missions/${mission.id}`
    const [treatments, entries, assignments] = await Promise.all([
      loadAll(api, `${base}/treatments/`, { signal: request.signal }),
      loadAll(api, `${base}/operation-log/`, { signal: request.signal }),
      loadAll(api, `${base}/helpers/`, { signal: request.signal }),
    ])
    if (request.signal.aborted) return
    const report = buildShiftReport({ mission, treatments, entries, assignments, ...bounds })
    status.value = 'PDF wird erstellt …'
    const { createShiftPdf, shiftFilename } = await import('../export/shiftPdf')
    const pdf = await createShiftPdf(report)
    if (request.signal.aborted) return
    pdf.save(shiftFilename(report))
    status.value = 'PDF erstellt und zum Download bereitgestellt.'
  } catch (failure) {
    if (!request.signal.aborted) { error.value = failure.message; status.value = '' }
    request.abort()
  } finally {
    if (controller === request) busy.value = false
  }
}
</script>

<template>
  <div class="shift-export">
    <header><p class="overline red">Einsatzdokumentation</p><h1>Schichtexport</h1><p class="muted">PDF für {{ mission.name }}</p></header>
    <form @submit.prevent="exportPdf">
      <fieldset :disabled="busy">
        <legend>Umfang</legend>
        <label class="mode"><input v-model="mode" type="radio" value="all">Kompletter Einsatz</label>
        <label class="mode"><input v-model="mode" type="radio" value="range">Zeitraum von – bis</label>
        <div v-if="mode === 'range'" class="range">
          <label>Von (Europe/Berlin)<input v-model="from" type="datetime-local" required></label>
          <label>Bis (Europe/Berlin)<input v-model="to" type="datetime-local" required :min="from"></label>
        </div>
      </fieldset>
      <p v-if="mode === 'range'" class="muted">Von einschließlich, Bis ausschließlich. Behandlungen und Helferdienste, die in den Zeitraum hineinreichen, sind enthalten.</p>
      <ol>
        <li>Übersicht mit Einsatzzahlen und Zeiten</li>
        <li>Patienten mit Name, Geburtstag, Entlassungsort und Stichwort</li>
        <li>Einsatztagebuch (ETB)</li>
        <li>Helfer, sortiert nach Gliederung</li>
      </ol>
      <p class="muted">Alle Zeiten in Europe/Berlin. Das PDF wird im Browser erstellt.</p>
      <p v-if="missing.length" class="error" role="alert">Für den vollständigen Export fehlen Leserechte: {{ missing.join(', ') }}.</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="status" role="status" aria-live="polite">{{ status }}</p>
      <button class="primary" :disabled="busy || missing.length">{{ busy ? 'Export läuft …' : 'PDF herunterladen' }}</button>
    </form>
  </div>
</template>

<style scoped>
.shift-export{padding:42px 4%;max-width:1100px;margin:auto}.shift-export h1{font-size:36px;margin-bottom:8px}.shift-export form{background:white;padding:28px;border:1px solid #dce4e8;border-radius:10px;margin-top:28px}fieldset{border:0;padding:0;margin:0}legend{font-weight:700;margin-bottom:16px}.mode{display:flex;align-items:center;gap:10px;margin:12px 0;font-size:15px}.mode input{width:auto}.range{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px}.range label{margin-top:12px}ol{padding-left:22px;line-height:1.9;margin:24px 0}.muted{font-size:14px}@media(max-width:700px){.shift-export{padding:24px 16px}.shift-export form{padding:20px}.range{grid-template-columns:1fr}}
</style>
