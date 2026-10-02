import { computed, onMounted, ref } from 'vue'
import { api, logout } from '../api'

export function useAppState() {
  const stage = ref('loading')
  const user = ref(null)
  const missions = ref([])
  const selected = ref(null)
  const error = ref('')
  const busy = ref(false)
  const ssoEnabled = ref(false)
  const active = computed(() => missions.value.filter((mission) => mission.state === 'ACTIVE'))

  async function loadMissions() {
    missions.value = await api('/missions/')
  }

  async function restoreSession() {
    let session
    try {
      session = await api('/auth/session/')
    } catch (requestError) {
      error.value = requestError.message
      stage.value = 'login'
      return
    }
    ssoEnabled.value = session.sso_enabled
    if (!session.authenticated) {
      if (new URLSearchParams(window.location.search).get('sso') === 'denied') {
        error.value = 'SSO-Anmeldung fehlgeschlagen. Benutzerkonto und Gruppenfreigabe prüfen.'
        window.history.replaceState({}, '', window.location.pathname)
      }
      stage.value = 'login'
      return
    }
    user.value = session.user
    stage.value = 'missions'
    try {
      await loadMissions()
    } catch (requestError) {
      missions.value = []
      error.value = requestError.message
    }
  }

  async function signIn(credentials) {
    busy.value = true
    error.value = ''
    user.value = null
    missions.value = []
    try {
      const response = await api('/auth/login/', {
        method: 'POST',
        body: JSON.stringify(credentials),
      })
      user.value = response.user
      stage.value = 'missions'
      await loadMissions()
    } catch (requestError) {
      error.value = requestError.message
    } finally {
      busy.value = false
    }
  }

  async function createMission(name) {
    busy.value = true
    error.value = ''
    try {
      const mission = await api('/missions/', {
        method: 'POST',
        body: JSON.stringify({ name, state: 'ACTIVE' }),
      })
      missions.value.push(mission)
      openMission(mission)
    } catch (requestError) {
      error.value = requestError.message
    } finally {
      busy.value = false
    }
  }

  function openMission(mission) {
    selected.value = mission
    stage.value = 'app'
  }

  function showMissions() {
    selected.value = null
    error.value = ''
    stage.value = 'missions'
  }

  onMounted(restoreSession)
  return { stage, user, active, selected, error, busy, ssoEnabled, signIn, createMission, openMission, showMissions, logout }
}
