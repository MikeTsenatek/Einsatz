<script setup>
import { computed, onMounted, ref, watch, watchEffect } from 'vue'
import { api } from '../api'

const props = defineProps({ modelValue: { default: null }, disabled: Boolean })
const emit = defineEmits(['update:modelValue'])
const entries = ref([])
const query = ref('')
const inputElement = ref(null)
const opened = ref(false)
const active = ref(-1)
const loading = ref(true)
const error = ref('')
const selected = computed(() => entries.value.find(item => item.id === props.modelValue))
const matches = computed(() => {
  const terms = query.value.toLocaleLowerCase('de').trim().split(/\s+/).filter(Boolean)
  return entries.value.filter(item => terms.every(term => item.label.toLocaleLowerCase('de').includes(term))).slice(0, 20)
})
watch(selected, (item, previous) => {
  if (item) query.value = item.label
  else if (query.value === previous?.label) query.value = ''
})
watchEffect(() => {
  inputElement.value?.setCustomValidity(!props.disabled && query.value.trim() && !selected.value ? 'Bitte einen vorhandenen HiOrg-Eintrag auswählen oder die Suche leeren.' : '')
})
watch(query, () => { active.value = -1 })

async function load() {
  loading.value = true
  error.value = ''
  try { entries.value = await api('/hiorgs/') }
  catch (requestError) { error.value = requestError.message }
  finally { loading.value = false }
}
onMounted(load)
function input(event) {
  query.value = event.target.value
  opened.value = true
  if (query.value !== selected.value?.label) emit('update:modelValue', null)
}
function select(item) {
  emit('update:modelValue', item.id)
  query.value = item.label
  opened.value = false
}
function close() {
  opened.value = false
}
function clear() {
  query.value = ''
  emit('update:modelValue', null)
}
function keydown(event) {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    opened.value = true
    active.value = Math.max(0, Math.min(matches.value.length - 1, active.value + (event.key === 'ArrowDown' ? 1 : -1)))
  } else if (event.key === 'Enter' && opened.value) {
    event.preventDefault()
    if (matches.value[active.value]) select(matches.value[active.value])
  } else if (event.key === 'Escape') close()
}
</script>

<template>
  <div class="hiorg-lookup">
    <label for="helper-hiorg">HiOrg - Kreisverband - Gemeinschaft - Gliederung <small>optional</small></label>
    <input ref="inputElement" id="helper-hiorg" :value="query" :disabled="disabled || loading" autocomplete="off"
      role="combobox" aria-autocomplete="list" aria-controls="hiorg-options" :aria-expanded="opened"
      :aria-activedescendant="active >= 0 && opened ? 'hiorg-option-' + active : undefined"
      aria-describedby="hiorg-status" @input="input" @focus="opened = true" @blur="close" @keydown="keydown">
    <p id="hiorg-status" class="muted" role="status">{{ loading ? 'HiOrg-Einträge werden geladen …' : selected ? 'Vorhandener Eintrag ausgewählt.' : 'Suchen und einen vorhandenen Eintrag auswählen. Freitext wird nicht gespeichert.' }}</p>
    <p v-if="error" class="error" role="alert">{{ error }} <button type="button" @click="load">Erneut laden</button></p>
    <ul v-if="opened && !disabled && !loading" id="hiorg-options" role="listbox" aria-label="HiOrg-Einträge">
      <li v-for="(item, index) in matches" :id="'hiorg-option-' + index" :key="item.id" role="option" :aria-selected="active === index" :class="{ active: active === index }" @pointerdown.prevent="select(item)">{{ item.label }}</li>
      <li v-if="!matches.length" role="presentation">Keine passenden Einträge.</li>
    </ul>
    <button v-if="modelValue && !disabled" type="button" class="secondary" @click="clear">Auswahl entfernen</button>
  </div>
</template>

<style scoped>
.hiorg-lookup{grid-column:1/-1}.hiorg-lookup label{margin:0 0 8px}.hiorg-lookup small{color:#8a98a3;font-weight:400}.hiorg-lookup p{font-size:12px;margin:8px 0}ul{list-style:none;margin:6px 0;padding:0;border:1px solid #d6dfe4;border-radius:8px;max-height:260px;overflow:auto;background:white}li{padding:10px 14px;cursor:pointer;font-size:13px}li:hover,li.active{background:#e8f0f4}.secondary{padding:8px 12px;font-size:12px}
</style>
