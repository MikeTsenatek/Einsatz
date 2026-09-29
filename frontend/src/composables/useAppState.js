import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

export function useAppState() {
  const stage = ref('loading')
  const user = ref(null)
  const missions = ref([])
  const selected = ref(null)
  const error = ref('')
  const busy = ref(false)
  const active = computed(() => missions.value.filter((mission) => mission.state === 'ACTIVE'))

  async function loadMissions() {
    missions.value = await api('/missions/')
  }

  async function restoreSession() {
    try {
      const session = await api('/auth/session/')
      if (!session.authenticated) {
        stage.value = 'login'
        return
      }
      user.value = session.user
      await loadMissions()
      stage.value = 'missions'
    } catch {
      stage.value = 'login'
    }
  }

  async function signIn(credentials) {
    busy.value = true
    error.value = ''
    try {
      const response = await api('/auth/login/', {
        method: 'POST',
        body: JSON.stringify(credentials),
      })
      user.value = response.user
      await loadMissions()
      stage.value = 'missions'
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

  async function logout() {
    await api('/auth/logout/', { method: 'POST' })
    user.value = null
    missions.value = []
    selected.value = null
    stage.value = 'login'
  }

  onMounted(restoreSession)
  return { stage, user, active, selected, error, busy, signIn, createMission, openMission, showMissions, logout }
}
