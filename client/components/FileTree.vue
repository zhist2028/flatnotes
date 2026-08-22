<template>
  <p v-if="tree.length === 0" class="text-center text-theme-text-muted">
    No notes
  </p>
  <ul v-else role="tree" aria-label="File tree" class="w-full">
    <FileTreeNode v-for="node in tree" :key="node.path" :node="node" />
  </ul>
</template>

<script setup>
import { computed } from "vue";

import FileTreeNode from "./FileTreeNode.vue";
import { buildTitleTree } from "../titleTree.js";

const props = defineProps({
  titles: {
    type: Array,
    default: () => [],
  },
});

const tree = computed(() => buildTitleTree(props.titles));
</script>
