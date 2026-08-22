<template>
  <li role="treeitem" :aria-expanded="hasChildren ? expanded : undefined">
    <div class="flex min-h-8 items-center">
      <button
        v-if="hasChildren"
        type="button"
        class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-lg text-theme-text-muted hover:bg-theme-background-elevated hover:text-theme-text"
        :aria-label="`${expanded ? 'Collapse' : 'Expand'} ${node.name}`"
        @click="toggle"
      >
        <span
          aria-hidden="true"
          class="transition-transform duration-150"
          :class="{ 'rotate-90': expanded }"
          >›</span
        >
      </button>
      <span v-else aria-hidden="true" class="w-7 shrink-0"></span>

      <RouterLink
        v-if="node.isNote"
        :to="{ name: 'note', params: { title: node.fullTitle } }"
        :title="node.fullTitle"
        class="min-w-0 truncate rounded px-1 py-0.5 text-theme-link hover:bg-theme-background-elevated hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-theme-link"
      >
        {{ node.name }}
      </RouterLink>
      <button
        v-else
        type="button"
        class="min-w-0 truncate rounded px-1 py-0.5 text-left text-theme-text hover:bg-theme-background-elevated focus-visible:outline focus-visible:outline-2 focus-visible:outline-theme-link"
        @click="toggle"
      >
        {{ node.name }}
      </button>
    </div>

    <ul
      v-if="hasChildren && expanded"
      role="group"
      class="ml-3 border-l border-theme-border pl-2"
    >
      <FileTreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
      />
    </ul>
  </li>
</template>

<script setup>
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

defineOptions({ name: "FileTreeNode" });

const props = defineProps({
  node: {
    type: Object,
    required: true,
  },
});

const expanded = ref(false);
const hasChildren = computed(() => props.node.children.length > 0);

function toggle() {
  if (hasChildren.value) {
    expanded.value = !expanded.value;
  }
}
</script>
