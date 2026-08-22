<template>
  <div class="flex h-full justify-center overflow-y-auto">
    <div
      class="flex w-full max-w-[900px] flex-col items-center px-1 pb-10 pt-[12vh] md:pt-[18vh]"
    >
      <Logo class="mb-5" />
      <SearchInput
        class="mb-8 w-full max-w-[500px] shadow-[0_0_20px] shadow-theme-shadow"
      />

      <div class="grid w-full grid-cols-1 gap-8 md:grid-cols-2 md:gap-10">
        <section v-if="!globalStore.config.quickAccessHide" class="min-w-0">
          <h2
            class="mb-3 text-center text-xs font-bold uppercase text-theme-text-very-muted"
          >
            {{ globalStore.config.quickAccessTitle }}
          </h2>
          <LoadingIndicator
            ref="recentLoadingIndicator"
            class="flex min-h-56 flex-col items-center"
            hideLoader
          >
            <p v-if="notes.length === 0" class="text-theme-text-muted">
              No notes
            </p>
            <RouterLink
              v-for="note in notes.slice(
                0,
                globalStore.config.quickAccessLimit,
              )"
              :key="note.title"
              :to="{ name: 'note', params: { title: note.title } }"
              class="mb-1 max-w-full"
            >
              <CustomButton :label="note.title" class="max-w-full" />
            </RouterLink>
            <RouterLink
              v-if="notes.length > globalStore.config.quickAccessLimit"
              :to="{
                name: 'search',
                query: {
                  term: globalStore.config.quickAccessTerm,
                  sortBy: searchSortOptions[globalStore.config.quickAccessSort],
                },
              }"
              title="Show more"
              ><CustomButton :iconPath="mdiDotsHorizontal"
            /></RouterLink>
          </LoadingIndicator>
        </section>

        <section
          class="min-w-0"
          :class="{
            'md:col-span-2': globalStore.config.quickAccessHide,
          }"
        >
          <h2
            class="mb-3 text-center text-xs font-bold uppercase text-theme-text-very-muted"
          >
            File Tree
          </h2>
          <LoadingIndicator
            ref="treeLoadingIndicator"
            class="min-h-56"
            hideLoader
          >
            <div class="max-h-96 overflow-y-auto pr-1">
              <FileTree :titles="allNoteTitles" />
            </div>
          </LoadingIndicator>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { mdiDotsHorizontal } from "@mdi/js";
import { useToast } from "primevue/usetoast";
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { apiErrorHandler, getNotes } from "../api.js";
import CustomButton from "../components/CustomButton.vue";
import FileTree from "../components/FileTree.vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import Logo from "../components/Logo.vue";
import { searchSortOptions } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import SearchInput from "../partials/SearchInput.vue";

const globalStore = useGlobalStore();
const recentLoadingIndicator = ref();
const treeLoadingIndicator = ref();
const notes = ref([]);
const allNoteTitles = ref([]);
const toast = useToast();

function loadRecentNotes() {
  if (globalStore.config.quickAccessHide) {
    return;
  }

  getNotes(
    globalStore.config.quickAccessTerm,
    globalStore.config.quickAccessSort,
    // Order by ascending if sorting by title, descending otherwise.
    globalStore.config.quickAccessSort === "title" ? "asc" : "desc",
    // Limit is increased by 1 to check if there are more notes than the limit.
    globalStore.config.quickAccessLimit + 1,
  )
    .then((data) => {
      notes.value = data;
      recentLoadingIndicator.value.setLoaded();
    })
    .catch((error) => {
      recentLoadingIndicator.value.setFailed();
      apiErrorHandler(error, toast);
    });
}

function loadFileTree() {
  getNotes("*", "title", "asc")
    .then((data) => {
      allNoteTitles.value = data.map((note) => note.title);
      treeLoadingIndicator.value.setLoaded();
    })
    .catch((error) => {
      treeLoadingIndicator.value.setFailed();
      apiErrorHandler(error, toast);
    });
}

onMounted(() => {
  loadRecentNotes();
  loadFileTree();
});
</script>
