<script setup lang="ts">
import { ref, useId } from 'vue'

/**
 * Vue 3.5+ Accessible Form Component
 * Demonstrates:
 * 1. Native useId() for SSR-safe unique ID generation.
 * 2. Automatic label-to-input and error-message ARIA linking.
 * 3. Focus restoration when rendering overlays via <Teleport>.
 */

const usernameId = useId()
const errorId = useId()

const username = ref('')
const errorMessage = ref('')
const isModalOpen = ref(false)
const triggerRef = ref<HTMLButtonElement | null>(null)

function validateInput() {
  if (username.value.length < 3) {
    errorMessage.value = 'Username must be at least 3 characters long.'
  } else {
    errorMessage.value = ''
  }
}

function openModal() {
  isModalOpen.value = true
}

function closeModal() {
  isModalOpen.value = false
  // Restore focus on modal close
  triggerRef.value?.focus()
}
</script>

<template>
  <div class="vue-a11y-form">
    <h2>Vue 3.5 Accessible Form</h2>

    <div class="form-group">
      <label :for="usernameId">Username</label>
      <input
        :id="usernameId"
        v-model="username"
        type="text"
        :aria-invalid="!!errorMessage"
        :aria-describedby="errorMessage ? errorId : undefined"
        @blur="validateInput"
      />
      <span v-if="errorMessage" :id="errorId" class="error-text" role="alert">
        {{ errorMessage }}
      </span>
    </div>

    <button ref="triggerRef" type="button" @click="openModal">
      Open Account Settings
    </button>

    <!-- Teleport Overlay with Focus Containment -->
    <Teleport to="body">
      <div
        v-if="isModalOpen"
        class="modal-backdrop"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        @keydown.esc="closeModal"
      >
        <div class="modal-card">
          <h3 id="modal-title">Account Settings</h3>
          <p>Configure your account preferences here.</p>
          <button type="button" @click="closeModal">Close Settings</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.vue-a11y-form { max-width: 400px; font-family: system-ui, sans-serif; }
.form-group { margin-bottom: 1rem; }
label { display: block; margin-bottom: 0.25rem; font-weight: bold; }
input { width: 100%; padding: 0.5rem; border: 1px solid #777; border-radius: 4px; }
input:focus-visible { outline: 3px solid #005fcc; }
.error-text { color: #d9381e; font-size: 0.875rem; display: block; margin-top: 0.25rem; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; }
.modal-card { background: white; padding: 1.5rem; border-radius: 8px; max-width: 500px; }
</style>
