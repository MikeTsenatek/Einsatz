<script setup>
import { ref } from 'vue'

defineProps({ missions: Array, busy: Boolean, error: String })
const emit = defineEmits(['create', 'open'])
const creating = ref(false)
const name = ref('')

function create() {
  emit('create', name.value)
}
</script>

<template>
  <section class="content">
    <div class="heading">
      <div>
        <p class="overline red">Einsatzübersicht</p>
        <h1>Einsatz auswählen</h1>
        <p class="muted">Wählen Sie einen laufenden Einsatz oder legen Sie einen neuen an.</p>
      </div>
      <button class="primary small" @click="creating = true">＋ Neuer Einsatz</button>
    </div>
    <form v-if="creating" class="create" @submit.prevent="create">
      <h3>Neuer Einsatz anlegen</h3>
      <p class="muted">Vergeben Sie einen eindeutigen Namen.</p>
      <div>
        <input v-model.trim="name" required maxlength="100" autofocus placeholder="z. B. Stadtfest Nord 2026" aria-label="Name des Einsatzes">
        <button class="primary small" :disabled="busy">{{ busy ? 'Wird angelegt …' : 'Anlegen' }}</button>
        <button type="button" class="secondary" @click="creating = false">Abbrechen</button>
      </div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </form>
    <div v-if="missions.length" class="grid">
      <button v-for="mission in missions" :key="mission.id" class="card" @click="emit('open', mission)">
        <span class="status">● Aktiv</span><i aria-hidden="true">⌖</i><strong>{{ mission.name }}</strong>
        <small>Einsatz öffnen <b>→</b></small>
      </button>
    </div>
    <div v-else class="empty">
      <i aria-hidden="true">⌖</i><h3>Noch kein aktiver Einsatz</h3><p>Erstellen Sie den ersten Einsatz, um loszulegen.</p>
    </div>
  </section>
</template>
