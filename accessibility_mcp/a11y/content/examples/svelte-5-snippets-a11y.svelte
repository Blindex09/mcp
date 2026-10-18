<script lang="ts">
  /**
   * Svelte 5 Snippets & Runes Accessible Component
   * Demonstrates:
   * 1. $state and $derived runes for accessible reactive state.
   * 2. {#snippet} composition preserving ARIA semantics.
   * 3. Roving tabindex and keyboard navigation.
   */

  let activeTab = $state('tab-1');
  let selectedContent = $derived(
    activeTab === 'tab-1' ? 'Account Profile Settings Content' : 'Security & Password Settings Content'
  );

  function selectTab(id: string) {
    activeTab = id;
  }
</script>

<!-- Snippet Definition for Tab Button -->
{#snippet tabButton(id: string, label: string)}
  <button
    type="button"
    role="tab"
    id={`btn-${id}`}
    aria-selected={activeTab === id}
    aria-controls={`panel-${id}`}
    tabindex={activeTab === id ? 0 : -1}
    onclick={() => selectTab(id)}
    onkeydown={(e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault();
        const nextId = id === 'tab-1' ? 'tab-2' : 'tab-1';
        selectTab(nextId);
        document.getElementById(`btn-${nextId}`)?.focus();
      }
    }}
  >
    {label}
  </button>
{/snippet}

<div class="svelte-tabs">
  <h2>Svelte 5 Accessible Tabs Snippet</h2>

  <div role="tablist" aria-label="Settings Categories">
    {@render tabButton('tab-1', 'Profile Settings')}
    {@render tabButton('tab-2', 'Security Settings')}
  </div>

  <div
    role="tabpanel"
    id={`panel-${activeTab}`}
    aria-labelledby={`btn-${activeTab}`}
    tabindex="0"
    class="tab-panel"
  >
    <p>{selectedContent}</p>
  </div>
</div>

<style>
  .svelte-tabs { max-width: 500px; font-family: system-ui, sans-serif; }
  [role="tablist"] { display: flex; gap: 0.5rem; border-bottom: 2px solid #ccc; }
  [role="tab"] { padding: 0.5rem 1rem; border: none; background: #eee; cursor: pointer; }
  [role="tab"][aria-selected="true"] { background: #005fcc; color: white; font-weight: bold; }
  [role="tab"]:focus-visible { outline: 3px solid #ffcc00; }
  .tab-panel { padding: 1rem; border: 1px solid #ccc; border-top: none; }
</style>
