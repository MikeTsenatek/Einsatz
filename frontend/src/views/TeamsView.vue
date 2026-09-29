<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api'

const props = defineProps({ mission: { type: Object, required: true } })
const assignments = ref([])
const teams = ref([])
const newTeamName = ref('')
const showArchive = ref(false)
const endingTeamId = ref(null)
const activeTeams = computed(() => teams.value.filter((team) => !team.end_date))
const archivedTeams = computed(() => teams.value.filter((team) => team.end_date))
const visibleTeams = computed(() => showArchive.value ? archivedTeams.value : activeTeams.value)
const selectableTeams = computed(() => teams.value.filter((team) => !team.end_date || team.id === editing.value?.team?.id))
const loading = ref(true)
const saving = ref(false)
const deletingHelperId = ref(null)
const error = ref('')
const formOpen = ref(false)
const editing = ref(null)
const editingTeamId = ref(null)
const teamForm = ref({ name: '', notes: '', planned_end_date: '' })
const teamSaving = ref(false)
const teamError = ref('')
const form = ref(emptyForm())
const showHelperArchive = ref(false)
const archivedAssignments = computed(() => assignments.value.filter((item) => item.end_date))
const visibleAssignments = computed(() => assignments.value.filter((item) => showHelperArchive.value ? item.end_date : !item.end_date))
const selectedHelper = ref(null)
const helperSuggestions = ref([])
const helperSearchBusy = ref(false)
const helperSearchError = ref('')
const helperSearchDone = ref(false)
let helperSearchTimer
let helperSearchController

function stopHelperSearch() {
  window.clearTimeout(helperSearchTimer)
  helperSearchController?.abort()
  helperSuggestions.value = []
  helperSearchBusy.value = false
  helperSearchError.value = ''
  helperSearchDone.value = false
}

watch([() => form.value.name, () => form.value.birthday, formOpen, editing], () => {
  stopHelperSearch()
  if (selectedHelper.value && (form.value.name !== selectedHelper.value.name || form.value.birthday !== (selectedHelper.value.birthday || ''))) selectedHelper.value = null
  if (!formOpen.value || editing.value || selectedHelper.value || form.value.name.trim().length < 2) return
  helperSearchBusy.value = true
  helperSearchTimer = window.setTimeout(async () => {
    const request = new AbortController()
    helperSearchController = request
    try {
      const suggestions = await api('/helpers/search/?' + new URLSearchParams({ name: form.value.name.trim() }), { signal: request.signal })
      if (!request.signal.aborted) {
        helperSuggestions.value = suggestions
        helperSearchDone.value = true
      }
    } catch (requestError) {
      if (!request.signal.aborted) helperSearchError.value = requestError.message
    } finally {
      if (!request.signal.aborted) helperSearchBusy.value = false
    }
  }, 250)
}, { flush: 'sync' })

function selectHelper(helper) {
  form.value.name = helper.name
  form.value.birthday = helper.birthday || ''
  selectedHelper.value = helper
  stopHelperSearch()
}

onBeforeUnmount(stopHelperSearch)

function localDateTime(value = new Date()) {
  const date = new Date(value)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

function emptyForm() {
  return { name: '', birthday: '', team_id: '', start_date: localDateTime(), planned_end_date: '', end_date: '' }
}

const activeCount = computed(() => assignments.value.filter((item) => !item.end_date).length)

function teamMembers(teamId) {
  const members = new Map()
  assignments.value
    .filter((item) => item.team?.id === teamId && (showArchive.value || !item.end_date))
    .forEach((item) => {
      const existing = members.get(item.helper.id)
      if (!existing || new Date(item.start_date) > new Date(existing.start_date)) {
        members.set(item.helper.id, item)
      }
    })
  return [...members.values()]
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [assignmentData, teamData] = await Promise.all([
      api('/missions/' + props.mission.id + '/helpers/'),
      api('/missions/' + props.mission.id + '/teams/'),
    ])
    assignments.value = assignmentData
    teams.value = teamData
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    loading.value = false
  }
}

function registerHelper() {
  selectedHelper.value = null
  editing.value = null
  form.value = emptyForm()
  formOpen.value = true
}

function editAssignment(item) {
  editing.value = item
  form.value = {
    name: item.helper.name,
    birthday: item.helper.birthday || '',
    team_id: item.team?.id || '',
    start_date: localDateTime(item.start_date),
    planned_end_date: item.planned_end_date ? localDateTime(item.planned_end_date) : '',
    end_date: item.end_date ? localDateTime(item.end_date) : '',
  }
  formOpen.value = true
}

async function save() {
  saving.value = true
  error.value = ''
  const payload = {
    team_id: form.value.team_id || null,
    start_date: new Date(form.value.start_date).toISOString(),
    planned_end_date: form.value.planned_end_date ? new Date(form.value.planned_end_date).toISOString() : null,
    end_date: form.value.end_date ? new Date(form.value.end_date).toISOString() : null,
  }
  if (!editing.value) {
    if (selectedHelper.value) payload.helper_id = selectedHelper.value.id
    else payload.helper_details = { name: form.value.name.trim(), birthday: form.value.birthday || null }
  }
  try {
    const base = '/missions/' + props.mission.id + '/helpers/'
    await api(editing.value ? base + editing.value.id + '/' : base, {
      method: editing.value ? 'PATCH' : 'POST', body: JSON.stringify(payload),
    })
    formOpen.value = false
    showHelperArchive.value = Boolean(form.value.end_date)
    await load()
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    saving.value = false
  }
}

async function deleteHelper(helper) {
  if (deletingHelperId.value !== null) return
  if (!window.confirm('Helfer „' + helper.name + '“ vollständig löschen? Alle Dienstzeiten in allen Einsätzen werden ebenfalls endgültig gelöscht. Verknüpfungen zu Behandlungen werden entfernt; die Behandlungen bleiben erhalten.')) return
  deletingHelperId.value = helper.id
  error.value = ''
  try {
    await api('/helpers/' + helper.id + '/', { method: 'DELETE' })
    stopHelperSearch()
    if (editing.value?.helper.id === helper.id || selectedHelper.value?.id === helper.id) {
      formOpen.value = false
      editing.value = null
      selectedHelper.value = null
      form.value = emptyForm()
    }
    assignments.value = assignments.value.filter((item) => item.helper.id !== helper.id)
    await load()
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    deletingHelperId.value = null
  }
}

async function endDuty(item) {
  error.value = ''
  try {
    await api('/missions/' + props.mission.id + '/helpers/' + item.id + '/', {
      method: 'PATCH', body: JSON.stringify({ end_date: new Date().toISOString() }),
    })
    await load()
  } catch (requestError) {
    error.value = requestError.message
  }
}

async function createTeam() {
  const name = newTeamName.value.trim()
  if (!name) return
  error.value = ''
  try {
    const team = await api('/missions/' + props.mission.id + '/teams/', {
      method: 'POST', body: JSON.stringify({ name }),
    })
    teams.value.push(team)
    teams.value.sort((left, right) => left.name.localeCompare(right.name, 'de'))
    newTeamName.value = ''
    form.value.team_id = team.id
  } catch (requestError) {
    error.value = requestError.message
  }
}

function editTeam(team) {
  editingTeamId.value = team.id
  teamError.value = ''
  teamForm.value = {
    name: team.name,
    notes: team.notes || '',
    planned_end_date: team.planned_end_date ? localDateTime(team.planned_end_date) : '',
  }
}

async function saveTeam() {
  if (teamSaving.value) return
  teamSaving.value = true
  teamError.value = ''
  try {
    const team = await api('/missions/' + props.mission.id + '/teams/' + editingTeamId.value + '/', {
      method: 'PATCH',
      body: JSON.stringify({
        name: teamForm.value.name.trim(),
        notes: teamForm.value.notes,
        planned_end_date: teamForm.value.planned_end_date ? new Date(teamForm.value.planned_end_date).toISOString() : null,
      }),
    })
    teams.value = teams.value.map((item) => item.id === team.id ? team : item)
      .sort((left, right) => left.name.localeCompare(right.name, 'de'))
    assignments.value = assignments.value.map((item) => item.team?.id === team.id ? { ...item, team } : item)
    editingTeamId.value = null
  } catch (requestError) {
    teamError.value = requestError.message
  } finally {
    teamSaving.value = false
  }
}

async function endTeamDuty(team) {
  if (endingTeamId.value !== null) return
  if (!window.confirm('Dienst für Team „' + team.name + '“ und alle Mitglieder im Dienst beenden und das Team archivieren?')) return
  endingTeamId.value = team.id
  error.value = ''
  try {
    await api('/missions/' + props.mission.id + '/teams/' + team.id + '/end-duty/', { method: 'PATCH' })
    editingTeamId.value = null
    formOpen.value = false
    await load()
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    endingTeamId.value = null
  }
}

async function deleteTeam(team) {
  if (!window.confirm('Team „' + team.name + '“ wirklich löschen? Die Helfer bleiben ohne Team erhalten.')) return
  error.value = ''
  try {
    await api('/missions/' + props.mission.id + '/teams/' + team.id + '/', {
      method: 'DELETE',
    })
    if (editingTeamId.value === team.id) editingTeamId.value = null
    await load()
  } catch (requestError) {
    error.value = requestError.message
  }
}
function formatDate(value) {
  return new Intl.DateTimeFormat('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(value))
}

onMounted(load)
</script>

<template>
  <div class="teams-view">
    <div class="teams-heading">
      <div><p class="overline red">Einsatzpersonal</p><h1>Helfer</h1><p class="muted">{{ activeCount }} im Dienst · {{ assignments.length }} Dienstzeiten insgesamt</p></div>
      <button class="primary small" @click="registerHelper">＋ Helfer registrieren</button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <form class="team-create" @submit.prevent="createTeam">
      <input v-model.trim="newTeamName" maxlength="100" placeholder="Neues Team benennen" aria-label="Teamname">
      <button class="secondary" :disabled="!newTeamName.trim()">＋ Team anlegen</button>
    </form>
    <div class="team-tabs" role="group" aria-label="Teamansicht">
      <button class="secondary" :aria-pressed="!showArchive" @click="showArchive = false">Aktive Teams ({{ activeTeams.length }})</button>
      <button class="secondary" :aria-pressed="showArchive" @click="showArchive = true">Archiv ({{ archivedTeams.length }})</button>
    </div>
    <p v-if="!loading && !visibleTeams.length" class="muted">{{ showArchive ? 'Keine archivierten Teams.' : 'Keine aktiven Teams.' }}</p>
    <section v-if="visibleTeams.length" class="team-list" aria-label="Teams">
      <article v-for="team in visibleTeams" :key="team.id">
        <div class="team-card__heading">
          <strong>{{ team.name }}</strong>
          <div class="team-card__actions">
            <button type="button" class="icon-button" :disabled="teamSaving || endingTeamId !== null" :aria-label="team.name + ' bearbeiten'" title="Team bearbeiten" @click="editTeam(team)">✎</button>
            <button type="button" class="icon-button danger-button" :disabled="teamSaving || endingTeamId !== null" :aria-label="team.name + ' löschen'" title="Team löschen" @click="deleteTeam(team)">⌫</button>
          </div>
        </div>
        <p v-if="team.end_date" class="team-planned-end">Dienst beendet: {{ formatDate(team.end_date) }}</p>
        <button v-else class="secondary team-end-button" :disabled="teamSaving || saving || endingTeamId !== null" @click="endTeamDuty(team)">{{ endingTeamId === team.id ? 'Wird beendet …' : 'Teamdienst beenden' }}</button>
        <div class="team-members">
          <span>Teammitglieder</span>
          <ul v-if="teamMembers(team.id).length">
            <li v-for="member in teamMembers(team.id)" :key="member.helper.id">
              {{ member.helper.name }} <small v-if="member.end_date">außer Dienst</small>
            </li>
          </ul>
          <p v-else>Keine Helfer zugeordnet</p>
        </div>
        <form v-if="editingTeamId === team.id" class="team-editor" @submit.prevent="saveTeam">
          <fieldset :disabled="teamSaving || endingTeamId !== null">
            <label>Teamname<input v-model.trim="teamForm.name" required maxlength="100"></label>
            <label>Notizen <small>optional</small><textarea v-model="teamForm.notes" rows="4" placeholder="Hinweise zum Team"></textarea></label>
            <label>Geplantes Dienstende <small>optional</small><input v-model="teamForm.planned_end_date" type="datetime-local"></label>
            <p v-if="teamError" class="error" role="alert">{{ teamError }}</p>
            <div class="team-editor__actions">
              <button type="button" class="secondary" @click="editingTeamId = null">Abbrechen</button>
              <button type="submit" class="primary small">{{ teamSaving ? 'Speichert …' : 'Speichern' }}</button>
            </div>
          </fieldset>
        </form>
        <template v-else>
          <p v-if="team.planned_end_date" class="team-planned-end">Geplant bis {{ formatDate(team.planned_end_date) }}</p>
          <div v-if="team.notes" class="team-notes"><strong>Notizen</strong><p>{{ team.notes }}</p></div>
        </template>
      </article>
    </section>
    <form v-if="formOpen" class="helper-form" @submit.prevent="save">
      <div><h3>{{ editing ? 'Dienstzeit bearbeiten' : 'Helfer registrieren' }}</h3><p class="muted">Ohne Endzeit befindet sich der Helfer aktuell im Dienst.</p></div>
      <div class="form-grid">
        <div class="helper-lookup">
          <label for="helper-name">Name</label>
          <input id="helper-name" v-model.trim="form.name" required maxlength="100" autocomplete="off" :disabled="Boolean(editing)" aria-describedby="helper-search-status">
          <p v-if="!editing" id="helper-search-status" class="helper-search-status" role="status">
            {{ selectedHelper ? 'Vorhandener Helfer ausgewählt.' : helperSearchBusy ? 'Frühere Helferlisten werden durchsucht …' : helperSearchDone && !helperSuggestions.length ? 'Keine passenden Helfer gefunden.' : 'Ab zwei Zeichen werden vorhandene Helfer vorgeschlagen.' }}
          </p>
          <p v-if="helperSearchError" class="error" role="alert">Helfersuche: {{ helperSearchError }}</p>
          <ul v-if="helperSuggestions.length" class="helper-suggestions" aria-label="Vorhandene Helfer">
            <li v-for="helper in helperSuggestions" :key="helper.id">
              <button type="button" @click="selectHelper(helper)"><strong>{{ helper.name }}</strong><span>{{ helper.birthday ? 'Geboren: ' + helper.birthday : 'Geburtsdatum unbekannt' }} · Nr. {{ helper.id }}</span></button>
            </li>
          </ul>
        </div>
        <label>Geburtsdatum <small>optional</small><input v-model="form.birthday" type="date" :disabled="Boolean(editing)"></label>
        <label>Team <small>optional</small><select v-model="form.team_id"><option value="">Kein Team</option><option v-for="team in selectableTeams" :key="team.id" :value="team.id">{{ team.name }}</option></select></label>
        <label>Dienstbeginn<input v-model="form.start_date" required type="datetime-local"></label>
        <label>Geplantes Dienstende <small>optional</small><input v-model="form.planned_end_date" type="datetime-local" :min="form.start_date"></label>
        <label>Dienstende <small>optional</small><input v-model="form.end_date" type="datetime-local" :min="form.start_date"></label>
      </div>
      <div class="operation-log-form__actions"><button type="button" class="secondary" @click="formOpen = false">Abbrechen</button><button class="primary small" :disabled="saving">{{ editing ? 'Speichern' : 'Registrieren' }}</button></div>
    </form>
    <div class="team-tabs" role="group" aria-label="Helferansicht">
      <button class="secondary" :aria-pressed="!showHelperArchive" @click="showHelperArchive = false">Helfer im Dienst ({{ activeCount }})</button>
      <button class="secondary" :aria-pressed="showHelperArchive" @click="showHelperArchive = true">Helferarchiv ({{ archivedAssignments.length }})</button>
    </div>
    <div v-if="loading" class="compact-empty">Helfer werden geladen …</div>
    <div v-else-if="visibleAssignments.length" class="helper-table-wrap">
      <table class="helper-table">
        <thead><tr><th>Helfer</th><th>Team</th><th>Dienstbeginn</th><th>Geplant bis</th><th>Dienstende</th><th>Status</th><th>Aktionen</th></tr></thead>
        <tbody><tr v-for="item in visibleAssignments" :key="item.id">
          <td><strong>{{ item.helper.name }}</strong><small v-if="item.helper.birthday">{{ item.helper.birthday }}</small></td>
          <td>{{ item.team?.name || '–' }}</td>
          <td>{{ formatDate(item.start_date) }}</td><td>{{ item.planned_end_date ? formatDate(item.planned_end_date) : (item.team?.planned_end_date ? formatDate(item.team.planned_end_date) + ' (Team)' : '–') }}</td><td>{{ item.end_date ? formatDate(item.end_date) : '–' }}</td>
          <td><span class="duty-status" :class="{ done: item.end_date }">{{ item.end_date ? 'Außer Dienst' : 'Im Dienst' }}</span></td>
          <td><div class="helper-actions"><button :disabled="deletingHelperId !== null" @click="editAssignment(item)">Bearbeiten</button><button v-if="!item.end_date" :disabled="deletingHelperId !== null" @click="endDuty(item)">Dienst beenden</button><button class="danger-button" :disabled="deletingHelperId !== null || saving || endingTeamId !== null" @click="deleteHelper(item.helper)">{{ deletingHelperId === item.helper.id ? 'Wird gelöscht …' : 'Helfer vollständig löschen' }}</button></div></td>
        </tr></tbody>
      </table>
    </div>
    <div v-else class="compact-empty">{{ showHelperArchive ? 'Keine beendeten Helferdienste für diesen Einsatz.' : 'Aktuell keine Helfer im Dienst.' }}</div>
  </div>
</template>
<style scoped>
.teams-view{padding:42px 4%;max-width:1400px;margin:0 auto}
.teams-heading{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin-bottom:28px}
.teams-heading h1{font-size:36px;margin-bottom:6px}
.team-tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
.team-tabs button[aria-pressed="true"]{background:#293b49;color:#fff}
.team-end-button{margin-top:12px;padding:8px 12px;font-size:12px}
.team-create{display:flex;justify-content:flex-end;gap:9px;margin-bottom:20px}
.team-create input{max-width:280px}
.team-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-bottom:20px}
.team-list article{display:block;background:#fff;border:1px solid #dce4e8;border-radius:8px;padding:14px}
.team-card__heading{display:flex;align-items:center;justify-content:space-between;gap:12px}
.team-card__actions{display:flex;gap:4px}
.icon-button{display:grid;place-items:center;width:32px;height:32px;border:0;border-radius:6px;background:#edf2f4;color:#315a70;font-size:17px}
.icon-button:hover{background:#dfe8ec}
.icon-button.danger-button{color:#a1443e}
.team-members{margin-top:12px;padding-top:11px;border-top:1px solid #e4eaed}
.team-members>span{color:#71808d;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px}
.team-members ul{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 0;padding:0;list-style:none}
.team-members li{padding:5px 8px;border-radius:16px;background:#edf2f4;font-size:12px}
.team-members li small{color:#87949d}
.team-members p{margin:7px 0 0;color:#87949d;font-size:12px}
.team-planned-end{margin:12px 0 0;color:#50606d;font-size:12px}
.team-editor{margin-top:16px;border-top:1px solid #e4eaed;padding-top:12px}
.team-editor fieldset{border:0;padding:0;margin:0;min-width:0}
.team-editor label{margin-top:12px}
.team-editor small{color:#71808d;font-weight:400}
.team-editor__actions{display:flex;justify-content:flex-end;flex-wrap:wrap;gap:8px;margin-top:16px}
.team-editor__actions button{padding:10px 12px}
.team-notes{margin-top:14px;padding-top:12px;border-top:1px solid #e4eaed;font-size:13px}
.team-notes strong{color:#50606d;font-size:12px}
.team-notes p{margin:6px 0 0;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}
.helper-lookup label{margin:0 0 8px}
.helper-search-status{margin:7px 0 0!important;color:#596570;font-size:12px;line-height:1.5}
.helper-suggestions{list-style:none;padding:0;margin:8px 0 0;border:1px solid #dce4e8;border-radius:6px;max-height:220px;overflow:auto}
.helper-suggestions button{display:flex;flex-direction:column;gap:4px;width:100%;border:0;border-bottom:1px solid #edf1f3;background:#fff;text-align:left;padding:10px 12px;color:#26333d}
.helper-suggestions button:hover,.helper-suggestions button:focus-visible{background:#edf2f4}
.helper-suggestions span{font-size:12px;color:#596570}
.helper-form{background:#fff;border:1px solid #dce4e8;border-top:4px solid #e64a40;border-radius:10px;padding:24px;margin-bottom:20px}
.helper-form h3,.helper-form p{margin-bottom:4px}
.helper-table-wrap{overflow-x:auto;background:#fff;border:1px solid #dce4e8;border-radius:10px}
.helper-table{width:100%;min-width:760px;border-collapse:collapse}
.helper-table th{padding:11px 13px;background:#edf2f4;border-bottom:1px solid #d3dde2;color:#50606d;font-size:11px;text-align:left;text-transform:uppercase;letter-spacing:.6px}
.helper-table td{padding:13px;border-bottom:1px solid #e3e9ec;font-size:13px}
.helper-table tbody tr:last-child td{border-bottom:0}
.helper-table td small{display:block;margin-top:3px;color:#71808d}
.duty-status{display:inline-block;padding:5px 8px;border-radius:20px;background:#e7f5ec;color:#39835b;font-size:10px;font-weight:700;text-transform:uppercase}
.duty-status.done{background:#edf1f3;color:#667680}
.helper-actions{display:flex;flex-wrap:wrap;gap:12px}
.helper-actions button.danger-button{color:#a1443e}
.helper-actions button{border:0;background:transparent;padding:3px 0;color:#315a70;font-size:12px}
.helper-actions button:hover{text-decoration:underline}
@media(max-width:760px){.teams-view{padding:28px 18px}.teams-heading{align-items:flex-start;flex-direction:column}}
</style>
