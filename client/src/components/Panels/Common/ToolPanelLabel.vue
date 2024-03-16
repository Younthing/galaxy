<template>
    <div
        v-b-tooltip.topright.hover.noninteractive
        :class="['tool-panel-label', isTopMenu && 'top-menu-panel']"
        tabindex="0"
        :title="description">
        {{ definition.text }}
        <ToolPanelLinks :links="definition.links" />
    </div>
</template>

<script>
import ToolPanelLinks from "./ToolPanelLinks";

export default {
    components: { ToolPanelLinks },
    props: {
        definition: {
            type: Object,
            required: true,
        },
        isTopMenu: {
            type: Boolean,
        },
    },
    computed: {
        description() {
            return this.definition.description;
        },
    },
};
</script>

<style scoped lang="scss">
.top-menu-panel {
    margin-left: 0 !important;
}
.tool-panel-label {
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
