<script setup>
import BrandLogo from '../components/BrandLogo.vue'

defineProps({
  variant: { type: String, default: 'app' },
  user: Object,
  mission: Object,
  activeView: String,
})
const emit = defineEmits(['navigate', 'change-mission', 'logout'])
const navigation = [
  { id: 'overview', icon: '▦', label: 'Übersicht' },
  { id: 'patients', icon: '♙', label: 'Patienten' },
  { id: 'operationLog', icon: '☷', label: 'Einsatztagebuch' },
  { id: 'teams', icon: '♧', label: 'Helfer' },
  { id: 'map', icon: '⌖', label: 'Karte' },
]
</script>

<template>
  <main v-if="variant === 'login'" class="login-page">
    <section class="login-panel" aria-labelledby="login-title">
      <header class="login-brand">
        <BrandLogo dark />
        <p>Einsatzleitsoftware</p>
      </header>
      <slot />
    </section>
  </main>
  <main v-else-if="variant === 'missions'" class="missionPage">
    <header>
      <BrandLogo dark />
      <div class="account">
        <span class="avatar">{{ user?.name?.[0]?.toUpperCase() }}</span>
        <span>{{ user?.name }}</span>
        <button @click="emit('logout')">Abmelden</button>
      </div>
    </header>
    <slot />
  </main>
  <main v-else class="shell">
    <aside>
      <BrandLogo />
      <nav aria-label="Hauptnavigation">
        <button
          v-for="item in navigation"
          :key="item.id"
          :class="{ on: activeView === item.id }"
          :aria-label="item.label"
          :aria-current="activeView === item.id ? 'page' : undefined"
          :disabled="item.disabled"
          @click="!item.disabled && emit('navigate', item.id)"
        >
          <span aria-hidden="true">{{ item.icon }}</span> <span>{{ item.label }}</span>
        </button>
      </nav>
      <button class="switch" aria-label="Einsatz wechseln" @click="emit('change-mission')">↔ <span>Einsatz wechseln</span></button>
    </aside>
    <section class="workspace">
      <header>
        <div><p class="overline red">Aktiver Einsatz</p><h2>{{ mission?.name }}</h2></div>
        <span class="status">● Einsatz aktiv</span>
      </header>
      <slot />
    </section>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  place-items: center;
  min-height: 100vh;
  min-height: 100svh;
  padding: 48px 24px;
  background: #f5f6f7;
}

.login-panel {
  width: 100%;
  max-width: 360px;
}

.login-brand {
  padding-bottom: 28px;
  margin-bottom: 32px;
  border-bottom: 1px solid #dce0e3;
}

.login-brand :deep(.logo) {
  gap: 10px;
  font-size: 20px;
  color: #26333d;
}

.login-brand :deep(.logo b) {
  width: 30px;
  height: 30px;
  border-radius: 4px;
  background: #34434e;
  font-size: 18px;
  font-style: normal;
}

.login-brand p {
  margin: 12px 0 0;
  color: #596570;
  font-size: 13px;
}

@media (max-width: 480px) {
  .login-page {
    padding: 40px 24px;
  }
}
</style>
