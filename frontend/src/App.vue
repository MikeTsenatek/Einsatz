<script setup>
import { ref, watch } from 'vue'
import { useAppState } from './composables/useAppState'
import BaseLayout from './layouts/BaseLayout.vue'
import LoadingScreen from './components/LoadingScreen.vue'
import LoginView from './views/LoginView.vue'
import MissionSelectView from './views/MissionSelectView.vue'
import DashboardView from './views/DashboardView.vue'
import OperationLogView from './views/OperationLogView.vue'
import PatientsView from './views/PatientsView.vue'
import MapView from './views/MapView.vue'
import TeamsView from './views/TeamsView.vue'
import StatisticsView from './views/StatisticsView.vue'

const app = useAppState()
const activeView = ref('overview')

watch(app.selected, () => {
  activeView.value = 'overview'
})
</script>

<template>
  <LoadingScreen v-if="app.stage.value === 'loading'" />
  <BaseLayout
    v-else
    :variant="app.stage.value"
    :user="app.user.value"
    :mission="app.selected.value"
    :active-view="activeView"
    @navigate="activeView = $event"
    @change-mission="app.showMissions"
    @logout="app.logout"
  >
    <LoginView
      v-if="app.stage.value === 'login'"
      :busy="app.busy.value"
      :error="app.error.value"
      :sso-enabled="app.ssoEnabled.value"
      @submit="app.signIn"
    />
    <MissionSelectView
      v-else-if="app.stage.value === 'missions'"
      :missions="app.active.value"
      :busy="app.busy.value"
      :error="app.error.value"
      :user="app.user.value"
      @create="app.createMission"
      @open="app.openMission"
    />
    <OperationLogView v-else-if="activeView === 'operationLog'" :mission="app.selected.value" :user="app.user.value" />
    <PatientsView v-else-if="activeView === 'patients'" :mission="app.selected.value" :user="app.user.value" />
    <MapView v-else-if="activeView === 'map'" :key="app.selected.value.id" :mission="app.selected.value" :user="app.user.value" />
    <TeamsView v-else-if="activeView === 'teams'" :mission="app.selected.value" :user="app.user.value" />
    <StatisticsView v-else-if="activeView === 'statistics'" :mission="app.selected.value" />
    <DashboardView v-else :mission="app.selected.value" :user="app.user.value" @navigate="activeView = $event" />
  </BaseLayout>
</template>
