<template>
    <div class="sample-inspector" :class="{ dark: theme === 'dark' }">
        <div class="comparison-header">
            <div>
                <span>{{ local('Before') }}</span>
                <strong>{{ beforeTitle }}</strong>
            </div>
            <div>
                <span>{{ local('After') }}</span>
                <strong>{{ afterTitle }}</strong>
            </div>
        </div>

        <div v-if="!afterSample" class="inspector-empty">
            <i class="ms-Icon ms-Icon--SearchData"></i>
            <span>{{ local('Select a sample to inspect') }}</span>
        </div>
        <div v-else class="field-list">
            <article
                v-for="field in fields"
                :key="field.key"
                class="field-row"
                :class="field.status"
            >
                <header>
                    <strong>{{ field.key }}</strong>
                    <span>{{ fieldStatusLabel(field.status) }}</span>
                </header>
                <div class="field-values">
                    <div class="value-cell before-value">
                        <value-preview :value="field.before" :theme="theme" />
                    </div>
                    <div class="value-cell after-value">
                        <value-preview :value="field.after" :theme="theme" />
                    </div>
                </div>
            </article>
        </div>
    </div>
</template>

<script>
import { mapState } from 'pinia'
import { useAppConfig } from '@/stores/appConfig'
import valuePreview from './valuePreview.vue'

export default {
    components: { valuePreview },
    props: {
        beforeSample: {
            default: null
        },
        afterSample: {
            default: null
        },
        beforeTitle: {
            default: ''
        },
        afterTitle: {
            default: ''
        },
        theme: {
            default: 'light'
        }
    },
    computed: {
        ...mapState(useAppConfig, ['local']),
        fields() {
            const before = this.beforeSample || {}
            const after = this.afterSample || {}
            const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])]
            return keys.map((key) => {
                const hasBefore = Object.prototype.hasOwnProperty.call(before, key)
                const hasAfter = Object.prototype.hasOwnProperty.call(after, key)
                let status = 'unchanged'
                if (!hasBefore && hasAfter) status = 'added'
                else if (hasBefore && !hasAfter) status = 'removed'
                else if (this.stableValue(before[key]) !== this.stableValue(after[key]))
                    status = 'changed'
                return { key, before: before[key], after: after[key], status }
            })
        }
    },
    methods: {
        stableValue(value) {
            if (value === undefined) return '__undefined__'
            if (value && typeof value === 'object') {
                try {
                    return JSON.stringify(value, Object.keys(value).sort())
                } catch (_) {
                    return String(value)
                }
            }
            return String(value)
        },
        fieldStatusLabel(status) {
            const labels = {
                unchanged: this.local('Unchanged'),
                added: this.local('Added'),
                removed: this.local('Removed'),
                changed: this.local('Changed')
            }
            return labels[status]
        }
    }
}
</script>

<style lang="scss">
.sample-inspector {
    --inspector-bg: #ffffff;
    --inspector-muted: #6b7280;
    --inspector-border: rgba(86, 99, 130, 0.16);

    min-width: 0;
    border: 1px solid var(--inspector-border);
    border-radius: 9px;
    overflow: hidden;

    &.dark {
        --inspector-bg: #282c35;
        --inspector-muted: #aeb5c2;
        --inspector-border: rgba(220, 225, 235, 0.12);
    }

    .comparison-header {
        min-height: 52px;
        padding: 8px 12px;
        background: rgba(88, 101, 135, 0.06);
        border-bottom: 1px solid var(--inspector-border);
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;

        div {
            min-width: 0;
            display: flex;
            flex-direction: column;
        }

        span {
            color: var(--inspector-muted);
            font-size: 9px;
            text-transform: uppercase;
        }

        strong {
            margin-top: 3px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 11px;
        }
    }

    .field-list {
        max-height: 468px;
        overflow: auto;
    }

    .field-row {
        border-bottom: 1px solid var(--inspector-border);

        &:last-child {
            border-bottom: 0;
        }

        > header {
            min-height: 30px;
            padding: 5px 10px;
            background: rgba(88, 101, 135, 0.035);
            display: flex;
            align-items: center;
            justify-content: space-between;

            strong {
                font-size: 11px;
            }

            span {
                color: var(--inspector-muted);
                font-size: 9px;
            }
        }

        &.changed > header,
        &.added > header,
        &.removed > header {
            background: rgba(217, 119, 6, 0.09);

            span {
                color: #b76205;
                font-weight: 700;
            }
        }
    }

    .field-values {
        display: grid;
        grid-template-columns: 1fr 1fr;
    }

    .value-cell {
        min-width: 0;
        min-height: 42px;
        padding: 8px 10px;

        &:first-child {
            border-right: 1px solid var(--inspector-border);
        }
    }

    .inspector-empty {
        min-height: 290px;
        color: var(--inspector-muted);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 7px;
        font-size: 12px;

        i {
            font-size: 28px;
        }
    }
}
</style>
