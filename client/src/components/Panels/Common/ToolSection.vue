<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useEventBus } from "@vueuse/core";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import { useConfig } from "@/composables/config";
import { type ToolSectionLabel, useToolStore } from "@/stores/toolStore";
import ariaAlert from "@/utils/ariaAlert";

import Tool from "./Tool.vue";
import ToolPanelLabel from "./ToolPanelLabel.vue";
import ToolPanelLinks from "./ToolPanelLinks.vue";

const emit = defineEmits<{
    (e: "onClick", tool: any, evt: Event): void;
    (e: "onOperation", tool: any, evt: Event): void;
}>();

const eventBus = useEventBus<string>("open-tool-section");

const props = defineProps({
    category: {
        type: Object,
        required: true,
    },
    queryFilter: {
        type: String,
        default: "",
    },
    disableFilter: {
        type: Boolean,
    },
    hideName: {
        type: Boolean,
    },
    operationTitle: {
        type: String,
        default: "",
    },
    operationIcon: {
        type: String,
        default: "",
    },
    toolKey: {
        type: String,
        default: "",
    },
    sectionName: {
        type: String,
        default: "default",
    },
    expanded: {
        type: Boolean,
        default: false,
    },
    sortItems: {
        type: Boolean,
        default: true,
    },
});

const { config, isConfigLoaded } = useConfig();
const toolStore = useToolStore();

const elems = computed(() => {
    if (props.category.elems !== undefined && props.category.elems.length > 0) {
        return props.category.elems;
    }
    if (props.category.tools !== undefined && props.category.tools.length > 0) {
        return props.category.tools.map((toolId: string) => {
            const tool = toolStore.getToolForId(toolId);
            if (!tool && typeof toolId !== "string") {
                return toolId as ToolSectionLabel;
            } else {
                return tool;
            }
        });
    }
    return [];
});

const name = computed(() => props.category.title || props.category.name || props.category.text);
const isSection = computed(() => props.category.tools !== undefined || props.category.elems !== undefined);
const hasElements = computed(() => elems.value.length > 0);
const title = computed(() => props.category.description);
const links = computed(() => props.category.links || {});
const isLabel = computed(() => props.category.model_class === "ToolSectionLabel");
const isLabelMenu = computed(() => isLabel.value && isSection);

const opened = ref(props.expanded || checkFilter());

const sortedElements = computed(() => {
    // If this.config.sortTools is true, sort the tools alphabetically
    // When administrators have manually inserted labels we respect
    // the order set and hope for the best from the integrated
    // panel.
    if (
        !checkFilter() &&
        isConfigLoaded.value &&
        config.value.toolbox_auto_sort === true &&
        props.sortItems === true &&
        !elems.value.some((el: ToolSectionLabel) => el.text !== undefined && el.text !== "")
    ) {
        const elements = [...elems.value];
        const sorted = elements.sort((a, b) => {
            const aNameLower = a.name.toLowerCase();
            const bNameLower = b.name.toLowerCase();
            if (aNameLower > bNameLower) {
                return 1;
            } else if (aNameLower < bNameLower) {
                return -1;
            } else {
                return 0;
            }
        });
        return Object.entries(sorted);
    } else {
        return Object.entries(elems.value);
    }
});

watch(
    () => props.queryFilter,
    () => {
        opened.value = checkFilter();
    }
);

watch(
    () => opened.value,
    (newVal: boolean, oldVal: boolean) => {
        if (newVal !== oldVal) {
            const currentState = newVal ? "opened" : "closed";
            ariaAlert(`${name.value} tools menu ${currentState}`);
        }
    }
);

onMounted(() => {
    eventBus.on(openToolSection);
});

onUnmounted(() => {
    eventBus.off(openToolSection);
});

function openToolSection(sectionId: string) {
    if (isSection.value && sectionId == props.category?.id) {
        toggleMenu(true);
    }
}
function checkFilter() {
    return !props.disableFilter && !!props.queryFilter;
}
function onClick(tool: any, evt: Event) {
    emit("onClick", tool, evt);
}
function onOperation(tool: any, evt: Event) {
    emit("onOperation", tool, evt);
}
function toggleMenu(nextState = !opened.value) {
    opened.value = nextState;
}
</script>

<template>
    <div v-if="isSection && hasElements" class="tool-panel-section">
        <div
            v-b-tooltip.topright.hover.noninteractive
            :class="['toolSectionTitle', `tool-menu-section-${sectionName}`]"
            :title="title">
            <a :class="['title-link', 'row-title']" href="javascript:void(0)" @click="toggleMenu()">
                <span class="name"> {{ name }} </span>
                <ToolPanelLinks v-if="links" :links="links" />
                <FontAwesomeIcon
                    icon="chevron-right"
                    :class="[opened && 'opened-arrow', props?.category?._parent_id && 'mr-3']" />
            </a>
        </div>
        <transition name="slide">
            <div v-if="opened" :class="isLabelMenu && 'ml-3'" data-description="opened tool panel section">
                <!-- 展开LabelMenu的子菜单 -->
                <template v-if="isLabelMenu">
                    <ToolSection
                        v-for="i in props.category.tools"
                        :key="i?.id"
                        :category="i"
                        :query-filter="props.queryFilter || undefined"
                        @onClick="onClick" />
                </template>
                <Tool
                    v-for="[key, el] in sortedElements"
                    v-else
                    :key="key"
                    class="ml-2"
                    :tool="el"
                    :tool-key="toolKey"
                    :hide-name="hideName"
                    :operation-title="operationTitle"
                    :operation-icon="operationIcon"
                    @onOperation="onOperation"
                    @onClick="onClick" />
            </div>
        </transition>
    </div>
    <div v-else>
        <ToolPanelLabel v-if="category.text" :definition="category" />
        <Tool
            v-else
            :tool="category"
            :hide-name="hideName"
            :operation-title="operationTitle"
            :operation-icon="operationIcon"
            @onOperation="onOperation"
            @onClick="onClick" />
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.row-title {
    display: flex !important;
    justify-content: space-between;
    align-items: center;
}

.opened-arrow {
    transform: rotate(90deg);
}
.tool-panel-label {
    background: darken($panel-bg-color, 5%);
    border-left: 0.25rem solid darken($panel-bg-color, 25%);
    font-size: $h5-font-size;
    font-weight: 600;
    padding-left: 0.75rem;
    padding-top: 0.25rem;
    padding-bottom: 0.25rem;
    text-transform: uppercase;
}

.tool-panel-section .tool-panel-label {
    /* labels within subsections */
    margin-left: 1.5rem;
    padding-top: 0.125rem;
    padding-bottom: 0.125rem;
}

.slide-enter-active {
    -moz-transition-duration: 0.2s;
    -webkit-transition-duration: 0.2s;
    -o-transition-duration: 0.2s;
    transition-duration: 0.2s;
    -moz-transition-timing-function: ease-in;
    -webkit-transition-timing-function: ease-in;
    -o-transition-timing-function: ease-in;
    transition-timing-function: ease-in;
}

.slide-leave-active {
    -moz-transition-duration: 0.2s;
    -webkit-transition-duration: 0.2s;
    -o-transition-duration: 0.2s;
    transition-duration: 0.2s;
    -moz-transition-timing-function: cubic-bezier(0, 1, 0.5, 1);
    -webkit-transition-timing-function: cubic-bezier(0, 1, 0.5, 1);
    -o-transition-timing-function: cubic-bezier(0, 1, 0.5, 1);
    transition-timing-function: cubic-bezier(0, 1, 0.5, 1);
}

.slide-enter-to,
.slide-leave {
    max-height: 100px;
    overflow: hidden;
}

.slide-enter,
.slide-leave-to {
    overflow: hidden;
    max-height: 0;
}

.title-link {
    &:deep(.tool-panel-links) {
        display: none;
    }

    &:hover,
    &:focus,
    &:focus-within {
        &:deep(.tool-panel-links) {
            display: inline;
        }
    }
}
</style>
