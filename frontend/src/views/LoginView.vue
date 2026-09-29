<script setup>
import { ref } from 'vue'

defineProps({ busy: Boolean, error: String, ssoEnabled: Boolean })
const emit = defineEmits(['submit'])
const username = ref('')
const password = ref('')
</script>

<template>
  <form :aria-busy="busy" @submit.prevent="emit('submit', { username, password })">
    <h1 id="login-title">Anmelden</h1>
    <p class="login-description">{{ ssoEnabled ? 'Melden Sie sich mit Ihrem Keycloak-Konto an.' : 'Geben Sie Ihre Zugangsdaten ein.' }}</p>
    <div v-if="!ssoEnabled" class="login-field">
      <label for="username">Benutzername</label>
      <input id="username" v-model.trim="username" required autofocus autocomplete="username" autocapitalize="none" :spellcheck="false">
    </div>
    <div v-if="!ssoEnabled" class="login-field">
      <label for="password">Passwort</label>
      <input id="password" v-model="password" required type="password" autocomplete="current-password">
    </div>
    <p v-if="error" class="login-error" role="alert">{{ error }}</p>
    <button v-if="!ssoEnabled" class="login-submit" type="submit" :disabled="busy">{{ busy ? 'Anmeldung läuft …' : 'Anmelden' }}</button>
    <a v-if="ssoEnabled" class="sso-login" href="/oidc/authenticate/">Mit Keycloak anmelden</a>
  </form>
</template>

<style scoped>
h1 {
  margin: 0 0 8px;
  color: #26333d;
  font-size: 26px;
  line-height: 1.3;
  letter-spacing: -.5px;
}

.login-description {
  margin: 0 0 28px;
  color: #596570;
  font-size: 14px;
  line-height: 1.5;
}

.login-field + .login-field {
  margin-top: 20px;
}

.login-field label {
  display: block;
  margin: 0 0 8px;
  color: #34434e;
  font-size: 13px;
  font-weight: 500;
}

.login-field input {
  min-height: 46px;
  padding: 11px 12px;
  border: 1px solid #c5ccd1;
  border-radius: 4px;
  background: #fff;
  color: #26333d;
  font-size: 16px;
}

.login-field input:focus {
  border-color: #536b7c;
  box-shadow: 0 0 0 3px #536b7c18;
}

.login-submit {
  width: 100%;
  min-height: 46px;
  margin-top: 28px;
  padding: 12px 16px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: #293b49;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
}

.login-submit:hover:not(:disabled) {
  background: #1c2c38;
}

.sso-login {
  display: block;
  margin-top: 12px;
  padding: 12px 16px;
  border: 1px solid #c5ccd1;
  border-radius: 4px;
  color: #293b49;
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  text-decoration: none;
}

.sso-login:hover {
  background: #f5f6f7;
}

.login-error {
  margin: 20px 0 0;
  padding: 12px;
  border-left: 3px solid #ae3932;
  background: #f9eae8;
  color: #922e28;
  font-size: 13px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

</style>
