<script setup>
defineProps({ dark: Boolean })
</script>

<template>
  <div class="logo" :class="{ dark }" aria-label="EinSatz">
    <b aria-hidden="true">E</b><span>EinSatz</span>
  </div>
</template>
