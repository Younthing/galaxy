<template>
    <div :class="className">
        <div
            v-for="(input, index) in transformInputs"
            :key="index"
            :class="input.model_class?.includes('row-item') && 'row-item'">
            <span>{{ input.type }}-{{ input.model_class }}</span>
            <div v-if="input.type == 'conditional'" class="ui-portlet-section mt-3">
                <div class="portlet-header">
                    <b>{{ input.test_param.label || input.test_param.name }}</b>
                </div>
                <div class="portlet-content">
                    <FormElement
                        :id="conditionalPrefix(input, input.test_param.name)"
                        v-model="input.test_param.value"
                        :type="input.test_param.type"
                        :help="input.test_param.help"
                        :refresh-on-change="false"
                        :disabled="sustainConditionals"
                        :attributes="input.test_param"
                        @change="onChange" />
                    <div v-for="(caseDetails, caseId) in input.cases" :key="caseId">
                        <FormNode
                            v-if="conditionalMatch(input, caseId)"
                            v-bind="$props"
                            :inputs="caseDetails.inputs"
                            :prefix="getPrefix(input.name)" />
                    </div>
                </div>
            </div>
            <div v-else-if="input.type == 'repeat'">
                <FormRepeat
                    :input="input"
                    :sustain-repeats="sustainRepeats"
                    :passthrough-props="$props"
                    :prefix="prefix"
                    @insert="() => repeatInsert(input)"
                    @delete="(id) => repeatDelete(input, id)"
                    @swap="(a, b) => repeatSwap(input, a, b)" />
            </div>
            <div v-else-if="input.type == 'section'">
                <FormCard :title="input.title || input.name" :expanded.sync="input.expanded" :collapsible="true">
                    <template v-slot:body>
                        <div v-if="input.help" class="my-2" data-description="section help">{{ input.help }}</div>
                        <FormNode v-bind="$props" :inputs="input.inputs" :prefix="getPrefix(input.name)" />
                    </template>
                </FormCard>
            </div>
            <FormElement
                v-else
                :id="getPrefix(input.name)"
                v-model="input.value"
                :title="input.label || input.name"
                :type="input.type"
                :error="input.error"
                :warning="input.warning"
                :help="input.help"
                :refresh-on-change="input.refresh_on_change"
                :attributes="input.attributes || input"
                :collapsed-enable-text="collapsedEnableText"
                :collapsed-enable-icon="collapsedEnableIcon"
                :collapsed-disable-text="collapsedDisableText"
                :collapsed-disable-icon="collapsedDisableIcon"
                :loading="loading"
                :workflow-building-mode="workflowBuildingMode"
                @change="onChange" />
        </div>
    </div>
</template>

<script>
import { set } from "vue";

import { matchCase } from "@/components/Form/utilities";

import FormCard from "./FormCard.vue";
import FormRepeat from "./FormRepeat.vue";
import FormElement from "@/components/Form/FormElement.vue";

export default {
    name: "FormNode",
    components: {
        FormCard,
        FormElement,
        FormRepeat,
    },
    props: {
        className: {
            type: String,
            default: "",
        },
        inputs: {
            type: Array,
            default: null,
        },
        loading: {
            type: Boolean,
            default: false,
        },
        prefix: {
            type: String,
            default: "",
        },
        sustainRepeats: {
            type: Boolean,
            default: false,
        },
        sustainConditionals: {
            type: Boolean,
            default: false,
        },
        collapsedEnableText: {
            type: String,
            default: null,
        },
        collapsedDisableText: {
            type: String,
            default: null,
        },
        collapsedEnableIcon: {
            type: String,
            default: null,
        },
        collapsedDisableIcon: {
            type: String,
            default: null,
        },
        onChange: {
            type: Function,
            required: true,
        },
        onChangeForm: {
            type: Function,
            required: true,
        },
        workflowBuildingMode: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        transformInputs() {
            const itemArr = [];
            const rowItemArr = [];
            const inputLength = this.inputs.length;
            this.inputs
                .filter((i) => i.type !== "hidden")
                .forEach((input, index) => {
                    if (
                        (index === inputLength - 1 && inputLength % 2 !== 0) ||
                        (input.type === "repeat" && input?.inputs?.length > 2)
                    ) {
                        input.model_class += "row-item";
                        rowItemArr.push(input);
                    } else {
                        itemArr.push(input);
                    }
                });
            itemArr.sort((i) => (["data", "conditional", "rules"].includes(i?.type) ? 1 : -1));
            return itemArr.concat(rowItemArr);
        },
    },
    methods: {
        getPrefix(name, index) {
            if (this.prefix) {
                return `${this.prefix}|${name}`;
            } else {
                return name;
            }
        },
        conditionalPrefix(input, name) {
            return this.getPrefix(`${input.name}|${name}`);
        },
        conditionalMatch(input, caseId) {
            return matchCase(input, input.test_param.value) == caseId;
        },
        repeatInsert(input) {
            const newInputs = structuredClone(input.inputs);

            set(input, "cache", input.cache ?? []);
            input.cache.push(newInputs);

            this.onChangeForm();
        },
        repeatDelete(input, cacheId) {
            input.cache.splice(cacheId, 1);
            this.onChangeForm();
        },
        repeatSwap(input, a, b) {
            const tmpA = input.cache[a];
            const tmpB = input.cache[b];

            input.cache.splice(a, 1, tmpB);
            input.cache.splice(b, 1, tmpA);

            this.onChangeForm();
        },
    },
};
</script>
<style lang="scss" scoped>
.row-item {
    width: 100% !important;
}
</style>
