<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { hasPermission } from '../permissions'

const props = defineProps({ mission: { type: Object, required: true }, user: Object })
const canAddTreatment = computed(() => hasPermission(props.user, 'patients.add_treatment'))
const canChangeTreatment = computed(() => hasPermission(props.user, 'patients.change_treatment'))
const canDeleteTreatment = computed(() => hasPermission(props.user, 'patients.delete_treatment'))
const canChangePatient = computed(() => hasPermission(props.user, 'patients.change_patient'))
const canDeletePatient = computed(() => hasPermission(props.user, 'patients.delete_patient'))
const treatments = ref([])
const treatmentKeywords = ref([])
const keywordAutocompleteOpen = ref(false)
const activeKeywordIndex = ref(-1)
const patientSuggestions = ref([])
const patientAutocompleteOpen = ref(false)
let patientSearchTimer
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const panel = ref(null)
const treatmentForm = ref({ patient: '', patient_name: '', patient_birthday: '', patient_age: '', start_date: localDateTime(), end_date: '', keyword: '', notes: '' })
const editingTreatment = ref(null)
const originalPatient = ref(null)
const patientChoiceRequired = ref(false)
const patientEditChoice = ref(null)
const historyPatient = ref(null)
const historyTreatments = ref([])
const historyLoading = ref(false)
const currentPage = ref(1)
const totalTreatments = ref(0)
const historyPage = ref(1)
const historyTotal = ref(0)
const pageSize = 25
const totalPages = computed(() => Math.max(1, Math.ceil(totalTreatments.value / pageSize)))
const historyTotalPages = computed(() => Math.max(1, Math.ceil(historyTotal.value / pageSize)))

function ageFromBirthday(value) {
  if (!value) return ''
  const [year, month, day] = value.split('-').map(Number)
  const today = new Date()
  let age = today.getFullYear() - year
  if (
    today.getMonth() + 1 < month
    || (today.getMonth() + 1 === month && today.getDate() < day)
  ) age -= 1
  return age
}

function syncTreatmentAge() {
  if (treatmentForm.value.patient_birthday) {
    treatmentForm.value.patient_age = ageFromBirthday(treatmentForm.value.patient_birthday)
  }
  patientDataChanged()
}


function localDateTime(value = new Date()) {
  const date = new Date(value)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

const unassignedCount = computed(() => treatments.value.filter((treatment) => !treatment.patient).length)
const filteredKeywords = computed(() => {
  const query = treatmentForm.value.keyword.trim().toLocaleLowerCase('de')
  if (query.length < 2) return []
  return treatmentKeywords.value
    .filter((keyword) => keyword.name.toLocaleLowerCase('de').includes(query))
    .slice(0, 10)
})

async function load(page = 1) {
  loading.value = true
  error.value = ''
  try {
    const [treatmentData, keywordData] = await Promise.all([
      api('/missions/' + props.mission.id + '/treatments/?page=' + page),
      api('/treatment-keywords/'),
    ])
    treatments.value = treatmentData.results
    totalTreatments.value = treatmentData.count
    currentPage.value = page
    treatmentKeywords.value = keywordData
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    loading.value = false
  }
}


function startTreatment() {
  editingTreatment.value = null
  originalPatient.value = null
  patientChoiceRequired.value = false
  patientEditChoice.value = null
  historyPatient.value = null
  historyTreatments.value = []
  treatmentForm.value = {
    patient: '', patient_name: '', patient_birthday: '', patient_age: '', start_date: localDateTime(), end_date: '', keyword: '', notes: '',
  }
  panel.value = 'treatment'
}

function editTreatment(treatment) {
  editingTreatment.value = treatment
  const patient = treatment.patient
  originalPatient.value = patient ? { ...patient } : null
  patientChoiceRequired.value = false
  patientEditChoice.value = null
  treatmentForm.value = {
    patient: patient?.id || '',
    patient_name: patient?.name || '',
    patient_birthday: patient?.birthday || '',
    patient_age: patient?.age || '',
    start_date: localDateTime(treatment.start_date),
    end_date: treatment.end_date ? localDateTime(treatment.end_date) : '',
    keyword: treatment.keyword || '',
    notes: treatment.notes || '',
  }
  panel.value = 'treatment'
  if (patient) showPatientHistory(patient)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function closeTreatmentForm() {
  panel.value = null
  editingTreatment.value = null
  originalPatient.value = null
  patientChoiceRequired.value = false
  patientEditChoice.value = null
  historyPatient.value = null
  historyTreatments.value = []
}

async function saveTreatment() {
  saving.value = true
  error.value = ''
  const original = originalPatient.value
  const linkedPatientChanged = original && treatmentForm.value.patient === original.id && (
    treatmentForm.value.patient_name.trim() !== original.name
    || (treatmentForm.value.patient_birthday || null) !== (original.birthday || null)
    || Number(treatmentForm.value.patient_age || 0) !== Number(original.age || 0)
  )
  if (linkedPatientChanged && !patientEditChoice.value) {
    patientChoiceRequired.value = true
    saving.value = false
    return
  }
  const payload = {
    patient: patientEditChoice.value === 'new' ? null : treatmentForm.value.patient || null,
    start_date: new Date(treatmentForm.value.start_date).toISOString(),
    end_date: treatmentForm.value.end_date
      ? new Date(treatmentForm.value.end_date).toISOString()
      : null,
    keyword: treatmentForm.value.keyword,
    notes: treatmentForm.value.notes,
  }
  if (treatmentForm.value.patient_name.trim()) {
    payload.patient_details = {
      name: treatmentForm.value.patient_name.trim(),
      birthday: treatmentForm.value.patient_birthday || null,
      age: treatmentForm.value.patient_age || null,
    }
  }
  if (patientEditChoice.value === 'new') payload.create_new_patient = true
  try {
    if (editingTreatment.value) {
      const updated = await api(
        '/missions/' + props.mission.id + '/treatments/' + editingTreatment.value.id + '/',
        { method: 'PATCH', body: JSON.stringify(payload) },
      )
      treatments.value = treatments.value.map((item) => item.id === updated.id ? updated : item)
    } else {
      const created = await api('/missions/' + props.mission.id + '/treatments/', {
        method: 'POST', body: JSON.stringify(payload),
      })
      treatments.value.unshift(created)
    }
    closeTreatmentForm()
    await load(1)
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    saving.value = false
  }
}

function choosePatientEdit(choice) {
  patientEditChoice.value = choice
  patientChoiceRequired.value = false
  saveTreatment()
}

async function completeTreatment(treatment) {
  if (!treatment.patient || !treatment.keyword?.trim() || treatment.end_date) return
  error.value = ''
  try {
    const updated = await api(
      '/missions/' + props.mission.id + '/treatments/' + treatment.id + '/',
      { method: 'PATCH', body: JSON.stringify({ end_date: new Date().toISOString() }) },
    )
    treatments.value = treatments.value.map((item) => item.id === updated.id ? updated : item)
  } catch (requestError) {
    error.value = requestError.message
  }
}

async function deleteTreatment(treatment) {
  if (!window.confirm("Diese Behandlung wirklich unwiderruflich löschen?")) return
  error.value = ""
  try {
    await api("/missions/" + props.mission.id + "/treatments/" + treatment.id + "/", { method: "DELETE" })
    if (editingTreatment.value?.id === treatment.id) closeTreatmentForm()
    await load(1)
  } catch (requestError) {
    error.value = requestError.message
  }
}

async function deletePatient(patient) {
  if (!window.confirm("Diesen Patienten und alle verknüpften Behandlungen wirklich unwiderruflich löschen?")) return
  error.value = ""
  try {
    await api("/patients/" + patient.id + "/", { method: "DELETE" })
    closeTreatmentForm()
    await load(1)
  } catch (requestError) {
    error.value = requestError.message
  }
}

async function showPatientHistory(patient) {
  if (!patient) return
  historyPatient.value = patient
  historyTreatments.value = []
  historyLoading.value = true
  error.value = ''
  try {
    await loadPatientHistory(patient.id, 1)
  } catch (requestError) {
    error.value = requestError.message
    historyPatient.value = null
  } finally {
    historyLoading.value = false
  }
}

async function loadPatientHistory(patientId, page) {
  historyLoading.value = true
  try {
    const data = await api('/patients/' + patientId + '/treatments/?page=' + page)
    historyTreatments.value = data.results
    historyTotal.value = data.count
    historyPage.value = page
  } finally {
    historyLoading.value = false
  }
}

function patientDataChanged() {
  patientEditChoice.value = null
  patientChoiceRequired.value = false
  if (treatmentForm.value.patient) {
    patientSuggestions.value = []
    patientAutocompleteOpen.value = false
    return
  }
  window.clearTimeout(patientSearchTimer)
  const name = treatmentForm.value.patient_name.trim()
  if (name.length < 2) {
    patientSuggestions.value = []
    patientAutocompleteOpen.value = false
    return
  }
  patientSearchTimer = window.setTimeout(searchPatients, 250)
}

async function searchPatients() {
  if (treatmentForm.value.patient) return
  if (!hasPermission(props.user, 'patients.view_patient')) {
    patientSuggestions.value = []
    patientAutocompleteOpen.value = false
    return
  }
  const name = treatmentForm.value.patient_name.trim()
  if (name.length < 2) return
  const params = new URLSearchParams({ mission: props.mission.id, name })
  if (treatmentForm.value.patient_birthday) {
    params.set('birthday', treatmentForm.value.patient_birthday)
  }
  try {
    patientSuggestions.value = await api('/patients/search/?' + params)
    patientAutocompleteOpen.value = true
  } catch (requestError) {
    patientSuggestions.value = []
    patientAutocompleteOpen.value = false
    error.value = requestError.message
  }
}

function selectPatient(patient) {
  treatmentForm.value.patient = patient.id
  treatmentForm.value.patient_name = patient.name
  treatmentForm.value.patient_birthday = patient.birthday || ''
  treatmentForm.value.patient_age = patient.age || ''
  patientSuggestions.value = []
  patientAutocompleteOpen.value = false
  showPatientHistory(patient)
}

function closePatientAutocomplete() {
  window.setTimeout(() => { patientAutocompleteOpen.value = false }, 120)
}

function moveKeywordSelection(step) {
  if (!filteredKeywords.value.length) return
  keywordAutocompleteOpen.value = true
  activeKeywordIndex.value =
    (activeKeywordIndex.value + step + filteredKeywords.value.length)
    % filteredKeywords.value.length
}

function selectActiveKeyword(event) {
  const keyword = filteredKeywords.value[activeKeywordIndex.value]
  if (!keyword) return
  event?.preventDefault()
  selectKeyword(keyword)
}

function selectKeyword(keyword) {
  treatmentForm.value.keyword = keyword.name
  keywordAutocompleteOpen.value = false
  activeKeywordIndex.value = -1
}

function closeKeywordAutocomplete() {
  window.setTimeout(() => { keywordAutocompleteOpen.value = false }, 120)
}

function formatDate(value) {
  return new Intl.DateTimeFormat('de-DE', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(new Date(value))
}

onMounted(load)
</script>

<template>
  <div class="patients-view">
    <div class="patients-heading">
      <div><p class="overline red">Patientenversorgung</p><h1>Behandlungen</h1><p class="muted">{{ totalTreatments }} Behandlungen · {{ unassignedCount }} auf dieser Seite nicht zugeordnet</p></div>
      <div><button v-if="canAddTreatment" class="primary small" @click="startTreatment">＋ Behandlung</button></div>
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <form v-if="panel === 'treatment'" class="patient-form" @submit.prevent="saveTreatment">
      <div><h3>{{ editingTreatment ? 'Behandlung bearbeiten' : 'Behandlung beginnen' }}</h3><p class="muted">Sie kann ohne Patient begonnen, aber erst nach einer Zuordnung abgeschlossen werden.</p></div>
      <div class="form-grid">
        <div class="patient-capture form-grid__wide"><p>Patient <small>für Beginn optional</small></p><div class="form-grid"><label>Name<span class="autocomplete"><input v-model="treatmentForm.patient_name" maxlength="100" autocomplete="off" placeholder="Name eingeben" :disabled="Boolean(editingTreatment && treatmentForm.patient && !canChangePatient)" @input="patientDataChanged" @focus="searchPatients" @blur="closePatientAutocomplete"><ul v-if="patientAutocompleteOpen && patientSuggestions.length" role="listbox"><li v-for="patient in patientSuggestions" :key="patient.id" role="option" @mousedown.prevent="selectPatient(patient)"><strong>{{ patient.name }}</strong><small>{{ patient.birthday || (patient.age ? patient.age + ' Jahre' : 'Geburtsdatum unbekannt') }}</small></li></ul></span></label><label>Geburtsdatum <small>optional</small><input v-model="treatmentForm.patient_birthday" type="date" :disabled="Boolean(editingTreatment && treatmentForm.patient && !canChangePatient)" @input="syncTreatmentAge"></label><label>Alter <small>{{ treatmentForm.patient_birthday ? 'aus Geburtsdatum berechnet' : 'optional' }}</small><input v-model.number="treatmentForm.patient_age" type="number" min="0" max="130" :disabled="Boolean(treatmentForm.patient_birthday) || Boolean(editingTreatment && treatmentForm.patient && !canChangePatient)" @input="patientDataChanged"></label></div><span v-if="treatmentForm.patient" class="matched-patient">✓ Verknüpfter Patient – Änderungen aktualisieren seine Stammdaten</span><span v-else-if="treatmentForm.patient_name.trim()" class="new-patient">Neuer Patient, falls kein eindeutiger Treffer vorhanden ist</span></div><label>Beginn<input v-model="treatmentForm.start_date" required type="datetime-local"></label><label v-if="editingTreatment">Ende <small>nur mit Patient</small><input v-model="treatmentForm.end_date" type="datetime-local" :disabled="!treatmentForm.patient && !treatmentForm.patient_name.trim()"></label>
        <label>Stichwort <small>zum Abschließen erforderlich · Freitext</small><span class="autocomplete"><input v-model="treatmentForm.keyword" maxlength="200" autocomplete="off" role="combobox" aria-autocomplete="list" :aria-expanded="keywordAutocompleteOpen" :aria-activedescendant="activeKeywordIndex >= 0 ? 'keyword-option-' + activeKeywordIndex : undefined" aria-controls="keyword-suggestions" placeholder="Stichwort eingeben" @focus="keywordAutocompleteOpen = true" @input="keywordAutocompleteOpen = true; activeKeywordIndex = -1" @blur="closeKeywordAutocomplete" @keydown.down.prevent="moveKeywordSelection(1)" @keydown.up.prevent="moveKeywordSelection(-1)" @keydown.enter="selectActiveKeyword($event)" @keydown.esc="keywordAutocompleteOpen = false"><ul v-if="keywordAutocompleteOpen && filteredKeywords.length" id="keyword-suggestions" role="listbox"><li v-for="(keyword, index) in filteredKeywords" :id="'keyword-option-' + index" :key="keyword.id" role="option" :aria-selected="index === activeKeywordIndex" :class="{ active: index === activeKeywordIndex }" @mouseenter="activeKeywordIndex = index" @mousedown.prevent="selectKeyword(keyword)">{{ keyword.name }}</li></ul></span></label>
        <label class="form-grid__wide">Notizen <small>optional</small><textarea v-model.trim="treatmentForm.notes" rows="3"></textarea></label>
      </div>
      <div v-if="patientChoiceRequired" class="patient-edit-choice" role="alert">
        <div><strong>Patientendaten wurden geändert</strong><p>Sollen die Daten des verknüpften Patienten aktualisiert oder für diese Behandlung ein neuer Patient angelegt werden?</p></div>
        <div><button type="button" class="secondary" @click="choosePatientEdit('new')">Neuen Patienten anlegen</button><button type="button" class="primary small" @click="choosePatientEdit('linked')">Verknüpften Patienten aktualisieren</button></div>
      </div>
      <section v-if="historyPatient" class="treatment-form-history">
        <div class="patient-history__heading"><div><p class="overline red">Behandlungshistorie</p><h3>{{ historyPatient.display_name }}</h3></div></div>
        <div v-if="historyLoading" class="compact-empty">Historie wird geladen …</div>
        <div v-else-if="historyTreatments.length" class="treatment-table-wrap">
          <table class="treatment-table treatment-history-table">
            <thead><tr><th>Zeitraum</th><th>Stichwort</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="treatment in historyTreatments" :key="treatment.id">
                <td><time>{{ formatDate(treatment.start_date) }}</time><small v-if="treatment.end_date">bis {{ formatDate(treatment.end_date) }}</small></td>
                <td><strong>{{ treatment.keyword || '–' }}</strong></td>
                <td><span class="treatment-status" :class="{ done: treatment.end_date }">{{ treatment.end_date ? 'Abgeschlossen' : 'Laufend' }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="compact-empty">Keine bisherigen Behandlungen vorhanden.</div>
        <nav v-if="historyTotalPages > 1" class="pagination" aria-label="Historienseiten"><button class="secondary" :disabled="historyPage === 1 || historyLoading" @click="loadPatientHistory(historyPatient.id, historyPage - 1)">← Zurück</button><span>Seite {{ historyPage }} von {{ historyTotalPages }}</span><button class="secondary" :disabled="historyPage === historyTotalPages || historyLoading" @click="loadPatientHistory(historyPatient.id, historyPage + 1)">Weiter →</button></nav>
      </section>
      <div class="operation-log-form__actions"><button v-if="originalPatient && canDeletePatient && canDeleteTreatment" type="button" class="danger-button" @click="deletePatient(originalPatient)">Patient mit Behandlungen löschen</button><button type="button" class="secondary" @click="closeTreatmentForm">Abbrechen</button><button class="primary small" :disabled="saving">{{ editingTreatment ? 'Änderungen speichern' : 'Behandlung anlegen' }}</button></div>
    </form>


    <div v-if="loading" class="operation-log-empty">Behandlungen werden geladen …</div>
    <template v-else>
      <section class="patient-section">
        <h2>Behandlungen</h2>
        <div v-if="treatments.length" class="treatment-table-wrap">
          <table class="treatment-table">
            <colgroup><col class="col-period"><col class="col-patient"><col class="col-keyword"><col class="col-status"><col class="col-actions"></colgroup>
            <thead><tr><th>Zeitraum</th><th>Patient</th><th>Stichwort</th><th>Status</th><th><span class="sr-only">Aktionen</span></th></tr></thead>
            <tbody>
              <tr v-for="treatment in treatments" :key="treatment.id">
                <td><time>{{ formatDate(treatment.start_date) }}</time><small v-if="treatment.end_date">bis {{ formatDate(treatment.end_date) }}</small></td>
                <td><button v-if="treatment.patient && canChangeTreatment" type="button" class="treatment-patient-link" @click="editTreatment(treatment)"><strong>{{ treatment.patient.display_name }}</strong><small>{{ treatment.patient.birthday || (treatment.patient.age != null ? treatment.patient.age + ' Jahre' : 'Geburtsdatum unbekannt') }}</small></button><span v-else-if="treatment.patient" class="treatment-patient-link"><strong>{{ treatment.patient.display_name }}</strong><small>{{ treatment.patient.birthday || (treatment.patient.age != null ? treatment.patient.age + ' Jahre' : 'Geburtsdatum unbekannt') }}</small></span><span v-else class="muted">Nicht zugeordnet</span></td>
                <td><strong>{{ treatment.keyword || '–' }}</strong></td>
                <td><span class="treatment-status" :class="{ done: treatment.end_date }">{{ treatment.end_date ? 'Abgeschlossen' : 'Laufend' }}</span></td>
                <td><div class="treatment-table-actions"><button v-if="canChangeTreatment" @click="editTreatment(treatment)">Bearbeiten</button><button v-if="canChangeTreatment && !treatment.end_date" :disabled="!treatment.patient || !treatment.keyword?.trim()" :title="!treatment.patient ? 'Zum Abschließen zuerst einen Patienten zuordnen' : !treatment.keyword?.trim() ? 'Zum Abschließen ist ein Stichwort erforderlich' : 'Behandlung jetzt abschließen'" @click="completeTreatment(treatment)">Abschließen</button><button v-if="canDeleteTreatment" class="danger-button" @click="deleteTreatment(treatment)">Löschen</button></div></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="!error" class="compact-empty">Noch keine Behandlung erfasst.</div>
      </section>

      <nav v-if="totalPages > 1" class="pagination" aria-label="Behandlungsseiten"><button class="secondary" :disabled="currentPage === 1 || loading" @click="load(currentPage - 1)">← Zurück</button><span>Seite {{ currentPage }} von {{ totalPages }}</span><button class="secondary" :disabled="currentPage === totalPages || loading" @click="load(currentPage + 1)">Weiter →</button></nav>


    </template>
  </div>
</template>
