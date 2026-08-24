<template>
    <div class="value-preview" :class="{ dark: theme === 'dark' }">
        <span v-if="isEmpty" class="empty-value">—</span>
        <img
            v-else-if="mediaKind === 'image'"
            :src="stringValue"
            :alt="local('Image preview')"
            loading="lazy"
        />
        <audio
            v-else-if="mediaKind === 'audio'"
            :src="stringValue"
            controls
            preload="metadata"
        ></audio>
        <video
            v-else-if="mediaKind === 'video'"
            :src="stringValue"
            controls
            preload="metadata"
        ></video>
        <a v-else-if="mediaKind === 'pdf'" :href="stringValue" target="_blank" rel="noreferrer">
            <i class="ms-Icon ms-Icon--PDF"></i> {{ local('Open PDF') }}
        </a>
        <pre v-else>{{ displayValue }}</pre>
    </div>
</template>

<script>
import { mapState } from 'pinia'
import { useAppConfig } from '@/stores/appConfig'

export default {
    props: {
        value: {
            default: undefined
        },
        theme: {
            default: 'light'
        }
    },
    computed: {
        ...mapState(useAppConfig, ['local']),
        isEmpty() {
            return this.value === null || this.value === undefined || this.value === ''
        },
        stringValue() {
            return typeof this.value === 'string' ? this.value : ''
        },
        displayValue() {
            if (this.value && typeof this.value === 'object') {
                try {
                    return JSON.stringify(this.value, null, 2)
                } catch (_) {
                    return String(this.value)
                }
            }
            return String(this.value)
        },
        mediaKind() {
            if (typeof this.value !== 'string' || !/^(https?:|data:|blob:|\/)/i.test(this.value))
                return null
            const clean = this.value.split(/[?#]/)[0].toLowerCase()
            if (/^data:image\//.test(clean) || /\.(png|jpe?g|gif|webp|svg|bmp)$/.test(clean))
                return 'image'
            if (/^data:audio\//.test(clean) || /\.(mp3|wav|ogg|m4a|flac)$/.test(clean))
                return 'audio'
            if (/^data:video\//.test(clean) || /\.(mp4|webm|mov)$/.test(clean)) return 'video'
            if (/\.pdf$/.test(clean)) return 'pdf'
            return null
        }
    }
}
</script>

<style lang="scss">
.value-preview {
    max-width: 100%;

    pre {
        margin: 0;
        color: #273044;
        font:
            11px/1.5 ui-monospace,
            SFMono-Regular,
            Menlo,
            Consolas,
            monospace;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
    }

    &.dark pre {
        color: #e5e7eb;
    }

    .empty-value {
        color: #9ca3af;
    }

    img,
    video {
        display: block;
        max-width: 100%;
        max-height: 240px;
        border-radius: 6px;
        object-fit: contain;
    }

    audio {
        width: 100%;
        max-width: 360px;
    }

    a {
        color: #4f63d8;
        font-size: 11px;
        text-decoration: none;
    }
}
</style>
