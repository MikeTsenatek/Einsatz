<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { hasPermission } from '../permissions'

const props = defineProps({ mission: { type: Object, required: true }, user: Object })
const canCreateEntry = computed(() => hasPermission(props.user, 'missions.add_operationlogentry'))
const canChangeEntry = computed(() => hasPermission(props.user, 'missions.change_operationlogentry'))
const entries = ref([])
const priorities = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const showForm = ref(false)
const search = ref('')
const visibility = ref('all')
const editingEntry = ref(null)
const histories = ref({})
const openHistoryId = ref(null)
const historyLoading = ref(false)
const currentPage = ref(1)
const totalEntries = ref(0)
const pageSize = 25
const totalPages = computed(() => Math.max(1, Math.ceil(totalEntries.value / pageSize)))

function localDateTime(value = new Date()) {
  const date = new Date(value)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

const form = ref({
  sender: '',
  recipient: '',
  timestamp: localDateTime(),
  text: '',
  measure: '',
  priority: '',
})

function uniqueSuggestions(field) {
  return [...new Set(
    entries.value
      .map((entry) => entry[field].trim())
      .filter(Boolean),
  )].sort((left, right) => left.localeCompare(right, 'de'))
}

const senderSuggestions = computed(() => uniqueSuggestions('sender'))
const recipientSuggestions = computed(() => uniqueSuggestions('recipient'))

const filteredEntries = computed(() => {
  const query = search.value.trim().toLocaleLowerCase('de')
  return entries.value.filter((entry) => {
    if (visibility.value === 'active' && entry.is_struck_out) return false
    if (visibility.value === 'struck' && !entry.is_struck_out) return false
    if (!query) return true
    return [entry.sender, entry.recipient, entry.text, entry.measure]
      .some((value) => value.toLocaleLowerCase('de').includes(query))
  })
})

async function load(page = 1) {
  loading.value = true
  error.value = ''
  try {
    const [entryData, priorityData] = await Promise.all([
      api("/missions/" + props.mission.id + "/operation-log/?" + new URLSearchParams({ page, search: search.value, visibility: visibility.value })),
      api('/priorities/'),
    ])
    entries.value = entryData.results
    totalEntries.value = entryData.count
    currentPage.value = page
    priorities.value = priorityData
    if (!form.value.priority && priorityData.length) {
      form.value.priority = priorityData.find((item) => item.level === 3)?.id || priorityData[0].id
    }
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    loading.value = false
  }
}

let filterTimer
watch([search, visibility], () => {
  window.clearTimeout(filterTimer)
  filterTimer = window.setTimeout(() => load(1), 250)
})

function startCreate() {
  editingEntry.value = null
  form.value = {
    sender: '', recipient: '', timestamp: localDateTime(),
    text: '', measure: '', priority: form.value.priority,
  }
  showForm.value = true
}

async function startEdit(entry) {
  editingEntry.value = entry
  form.value = {
    sender: entry.sender, recipient: entry.recipient,
    timestamp: localDateTime(entry.timestamp), text: entry.text,
    measure: entry.measure, priority: entry.priority,
  }
  showForm.value = true
  await nextTick()
  document.querySelector('.operation-log-form')?.scrollIntoView({ behavior: 'smooth' })
}

function closeForm() {
  showForm.value = false
  editingEntry.value = null
}

async function saveEntry() {
  saving.value = true
  error.value = ''
  const payload = { ...form.value, timestamp: new Date(form.value.timestamp).toISOString() }
  try {
    if (editingEntry.value) {
      const updated = await api('/missions/' + props.mission.id + '/operation-log/' + editingEntry.value.id + '/', {
        method: 'PATCH', body: JSON.stringify(payload),
      })
      entries.value = entries.value.map((item) => item.id === updated.id ? updated : item)
      delete histories.value[updated.id]
    } else {
      const created = await api('/missions/' + props.mission.id + '/operation-log/', {
        method: 'POST', body: JSON.stringify(payload),
      })
      await load(1)
    }
    closeForm()
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    saving.value = false
  }
}

async function strikeEntry(entry) {
  if (!window.confirm('Diesen Eintrag wirklich unwiderruflich streichen?')) return
  error.value = ''
  try {
    const updated = await api(`/missions/${props.mission.id}/operation-log/${entry.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({ is_struck_out: true }),
    })
    entries.value = entries.value.map((item) => item.id === updated.id ? updated : item)
    delete histories.value[updated.id]
  } catch (requestError) {
    error.value = requestError.message
  }
}


async function toggleHistory(entry) {
  if (openHistoryId.value === entry.id) {
    openHistoryId.value = null
    return
  }
  openHistoryId.value = entry.id
  if (histories.value[entry.id]) return
  historyLoading.value = true
  try {
    histories.value[entry.id] = await api(
      '/missions/' + props.mission.id + '/operation-log/' + entry.id + '/history/',
    )
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    historyLoading.value = false
  }
}

const fieldLabels = {
  sender: 'Von', recipient: 'An', timestamp: 'Zeitpunkt', text: 'Meldung',
  measure: 'Maßnahme', priority: 'Priorität', is_struck_out: 'Status',
}
const actionLabels = { create: 'Angelegt', update: 'Geändert', delete: 'Gelöscht' }
function displayValue(value) {
  if (value === null || value === undefined || value === '') return '–'
  if (value === 'True' || value === true) return 'Gestrichen'
  if (value === 'False' || value === false) return 'Gültig'
  return String(value)
}

function formatDate(value) {
  return new Intl.DateTimeFormat('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(new Date(value))
}

onMounted(load)
</script>

<template>
  <div class="operation-log">
    <div class="operation-log__heading">
      <div>
        <p class="overline red">Dokumentation</p>
        <h1>Einsatztagebuch</h1>
        <p class="muted">{{ totalEntries }} protokollierte {{ totalEntries === 1 ? 'Meldung' : 'Meldungen' }}</p>
      </div>
      <button v-if="canCreateEntry" class="primary small" @click="startCreate">＋ Neuer Eintrag</button>
    </div>

    <form v-if="showForm" class="operation-log-form" @submit.prevent="saveEntry">
      <div class="operation-log-form__title">
        <div><h3>{{ editingEntry ? 'Eintrag bearbeiten' : 'Eintrag erfassen' }}</h3><p class="muted">{{ editingEntry ? 'Die Änderung wird im Auditlog nachvollziehbar gespeichert.' : 'Der Eintrag wird dauerhaft und auditierbar gespeichert.' }}</p></div>
        <button type="button" class="operation-log-form__close" aria-label="Formular schließen" @click="closeForm">×</button>
      </div>
      <div class="form-grid">
        <label>Von <small>optional</small><input v-model.trim="form.sender" list="sender-suggestions" maxlength="100" autocomplete="off" placeholder="z. B. Einsatzleitung"><datalist id="sender-suggestions"><option v-for="sender in senderSuggestions" :key="sender" :value="sender" /></datalist></label>
        <label>An <small>optional</small><input v-model.trim="form.recipient" list="recipient-suggestions" maxlength="100" autocomplete="off" placeholder="z. B. San-Team 1"><datalist id="recipient-suggestions"><option v-for="recipient in recipientSuggestions" :key="recipient" :value="recipient" /></datalist></label>
        <label>Zeitpunkt<input v-model="form.timestamp" required type="datetime-local"></label>
        <label>Priorität<select v-model="form.priority" required><option disabled value="">Bitte wählen</option><option v-for="priority in priorities" :key="priority.id" :value="priority.id">{{ priority.level }} · {{ priority.name }}</option></select></label>
        <label class="form-grid__wide">Meldung<textarea v-model.trim="form.text" required rows="3" placeholder="Was ist passiert?"></textarea></label>
        <label class="form-grid__wide">Maßnahme <small>optional</small><textarea v-model.trim="form.measure" rows="2" placeholder="Was wurde veranlasst?"></textarea></label>
      </div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <div class="operation-log-form__actions"><button type="button" class="secondary" @click="closeForm">Abbrechen</button><button class="primary small" :disabled="saving">{{ saving ? 'Wird gespeichert …' : editingEntry ? 'Änderungen speichern' : 'Eintrag speichern' }}</button></div>
    </form>

    <div class="operation-log-toolbar">
      <input v-model="search" type="search" placeholder="Einträge durchsuchen …" aria-label="Einträge durchsuchen">
      <select v-model="visibility" aria-label="Einträge filtern"><option value="all">Alle Einträge</option><option value="active">Nur gültige</option><option value="struck">Nur gestrichene</option></select>
    </div>

    <p v-if="error && !showForm" class="error" role="alert">{{ error }}</p>
    <div v-if="loading" class="operation-log-empty">Einträge werden geladen …</div>
    <div v-else-if="filteredEntries.length" class="operation-log-table-wrap">
      <table class="operation-log-table">
        <colgroup><col style="width: 5rem"><col class="col-time"><col class="col-priority"><col class="col-route"><col class="col-route"><col class="col-message"><col class="col-actions"></colgroup>
        <thead><tr><th>Nr.</th><th>Zeitpunkt</th><th>Priorität</th><th>Von</th><th>An</th><th>Meldung und Maßnahme</th><th><span class="sr-only">Aktionen</span></th></tr></thead>
        <tbody>
          <template v-for="entry in filteredEntries" :key="entry.id">
            <tr class="operation-log-row" :class="{ 'operation-log-row--struck': entry.is_struck_out }">
              <td>{{ entry.number }}</td>
              <td><time :datetime="entry.timestamp">{{ formatDate(entry.timestamp) }}</time></td>
              <td><span class="priority" :class="`priority--${entry.priority_level}`">P{{ entry.priority_level }} · {{ entry.priority_name }}</span><span v-if="entry.is_struck_out" class="struck-label">Gestrichen</span></td>
              <td class="route-cell">{{ entry.sender || '–' }}</td>
              <td class="route-cell">{{ entry.recipient || '–' }}</td>
              <td class="message-cell"><p>{{ entry.text }}</p><div v-if="entry.measure"><span>Maßnahme</span>{{ entry.measure }}</div></td>
              <td><div class="operation-log-entry__actions"><button v-if="canChangeEntry && !entry.is_struck_out" @click="startEdit(entry)">Bearbeiten</button><button @click="toggleHistory(entry)">{{ openHistoryId === entry.id ? 'Verlauf schließen' : 'Verlauf' }}</button><button v-if="canChangeEntry && !entry.is_struck_out" class="strike-button" @click="strikeEntry(entry)">Streichen</button></div></td>
            </tr>
            <tr v-if="openHistoryId === entry.id" class="operation-log-history-row">
              <td colspan="7">
                <section class="audit-history">
                  <p v-if="historyLoading">Verlauf wird geladen …</p>
                  <template v-else-if="histories[entry.id]?.length">
                    <article v-for="log in histories[entry.id]" :key="log.id" class="audit-event">
                      <div><strong>{{ actionLabels[log.action] || log.action }}</strong><span>{{ formatDate(log.timestamp) }} · {{ log.actor?.name || 'System' }}</span></div>
                      <dl><template v-for="(values, field) in log.changes" :key="field"><dt>{{ fieldLabels[field] || field }}</dt><dd><del>{{ displayValue(values[0]) }}</del><span>→</span><ins>{{ displayValue(values[1]) }}</ins></dd></template></dl>
                    </article>
                  </template>
                  <p v-else>Keine Historie vorhanden.</p>
                </section>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
    <div v-else-if="!error" class="operation-log-empty"><i aria-hidden="true">☷</i><h3>Keine Einträge gefunden</h3><p>{{ entries.length ? 'Passen Sie Suche oder Filter an.' : 'Erfassen Sie den ersten Eintrag für diesen Einsatz.' }}</p></div>
    <nav v-if="totalPages > 1" class="pagination" aria-label="ETB-Seiten"><button class="secondary" :disabled="currentPage === 1 || loading" @click="load(currentPage - 1)">← Zurück</button><span>Seite {{ currentPage }} von {{ totalPages }}</span><button class="secondary" :disabled="currentPage === totalPages || loading" @click="load(currentPage + 1)">Weiter →</button></nav>
  </div>
</template>
