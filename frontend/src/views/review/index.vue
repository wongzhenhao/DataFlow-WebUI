<template>
    <div class="result-viewer" :class="{ dark: theme === 'dark' }">
        <header class="viewer-header">
            <div class="brand-block">
                <img :src="logo" alt="DataFlow" />
                <div>
                    <p class="eyebrow">AI4S DATAFLOW</p>
                    <h1>{{ local('Operator Result Viewer') }}</h1>
                </div>
            </div>
            <div class="header-controls">
                <button class="credential-button" :class="{ configured: credentialConfiguredCount > 0 }"
                    @click="openCredentialPanel">
                    <i></i>
                    {{ local('Runtime credentials') }}
                    <span>{{ credentialConfiguredCount }}</span>
                </button>
                <span class="auto-refresh" :class="{ active: !overviewLoading }">
                    <i></i>{{ local('Auto refresh') }}
                </span>
                <button class="icon-button" :title="local('Refresh')" @click="loadOverview(false)">
                    ↻
                </button>
            </div>
        </header>

        <div class="viewer-body">
            <aside class="run-sidebar">
                <div class="sidebar-heading">
                    <div>
                        <p class="eyebrow">{{ local('Runs') }}</p>
                        <h2>{{ local('Processing history') }}</h2>
                    </div>
                    <span>{{ tasks.length }}</span>
                </div>

                <div v-if="overviewLoading && !tasks.length" class="sidebar-empty">
                    <span class="loading-ring"></span>
                    {{ local('Loading runs') }}
                </div>
                <div v-else-if="!tasks.length" class="sidebar-empty">
                    <strong>{{ local('No processing results yet') }}</strong>
                    <p>{{ local('Run a pipeline with Codex, then results will appear here automatically.') }}</p>
                </div>
                <div v-else class="run-list">
                    <button v-for="task in tasks" :key="task.task_id" class="run-card"
                        :class="{ active: selectedTaskId === task.task_id }" @click="selectTask(task)">
                        <span class="run-status" :class="statusClass(task.status)">{{ statusLabel(task.status) }}</span>
                        <strong>{{ taskPipelineName(task) }}</strong>
                        <small>{{ formatDate(task.completed_at || task.started_at) }}</small>
                        <code>{{ task.task_id }}</code>
                    </button>
                </div>
            </aside>

            <main class="result-main">
                <div v-if="!currentTask" class="main-empty">
                    <div class="empty-symbol">◇</div>
                    <h2>{{ local('Waiting for pipeline results') }}</h2>
                    <p>{{ local('Describe the processing task in Codex. This page only displays the completed pipeline and each operator result.') }}</p>
                </div>

                <template v-else>
                    <section class="run-overview">
                        <div>
                            <p class="eyebrow">{{ local('Selected Run') }}</p>
                            <h2>{{ currentPipelineName }}</h2>
                            <p class="run-description">
                                {{ formatDate(currentTask.completed_at || currentTask.started_at) }}
                                <span>·</span>
                                {{ currentTask.task_id }}
                            </p>
                        </div>
                        <div class="run-summary">
                            <div>
                                <strong>{{ completedSteps }}/{{ steps.length }}</strong>
                                <span>{{ local('operators completed') }}</span>
                            </div>
                            <div>
                                <strong>{{ currentTotal }}</strong>
                                <span>{{ local('current records') }}</span>
                            </div>
                            <span class="large-status" :class="statusClass(currentTask.status)">
                                {{ statusLabel(currentTask.status) }}
                            </span>
                        </div>
                    </section>

                    <section class="operator-section">
                        <div class="section-heading">
                            <div>
                                <p class="eyebrow">{{ local('Pipeline Operators') }}</p>
                                <h3>{{ local('Select an operator to view its result') }}</h3>
                            </div>
                            <button v-if="selectedStep !== null" class="download-button" @click="downloadStep">
                                ↓ {{ local('Download result') }}
                            </button>
                        </div>

                        <div v-if="steps.length" class="operator-track">
                            <button v-for="step in steps" :key="step.index" class="operator-card"
                                :class="[statusClass(step.status), { active: selectedStep === step.index }]"
                                @click="selectStep(step.index)">
                                <span class="operator-index">{{ step.index + 1 }}</span>
                                <span class="operator-copy">
                                    <strong>{{ step.name }}</strong>
                                    <small>{{ formatCount(step.sample_count) }} {{ local('records') }}</small>
                                </span>
                                <span class="operator-status">{{ statusLabel(step.status) }}</span>
                            </button>
                        </div>
                        <div v-else class="inline-empty">
                            {{ local('This run did not expose operator results.') }}
                        </div>
                    </section>

                    <section class="sample-section">
                        <div class="section-heading sample-heading">
                            <div>
                                <p class="eyebrow">{{ local('Operator Result') }}</p>
                                <h3>{{ selectedOperatorTitle }}</h3>
                            </div>
                            <div class="result-metrics">
                                <span>{{ formatCount(currentResult?.total_count) }} {{ local('records') }}</span>
                                <span v-if="previousResult">{{ retentionRate }} {{ local('retained') }}</span>
                            </div>
                        </div>

                        <div v-if="resultLoading" class="result-state">
                            <span class="loading-ring"></span>
                            {{ local('Loading operator result') }}
                        </div>
                        <div v-else-if="resultError" class="result-state error">
                            <strong>{{ local('Unable to load this result') }}</strong>
                            <p>{{ resultError }}</p>
                        </div>
                        <div v-else-if="!sampleRows.length" class="result-state">
                            <strong>{{ local('No result rows available') }}</strong>
                            <p>{{ local('The operator may still be running or may have produced an empty dataset.') }}</p>
                        </div>
                        <div v-else class="sample-layout">
                            <aside class="sample-list">
                                <div class="sample-list-heading">
                                    <span>{{ local('Samples') }}</span>
                                    <small>{{ sampleRows.length }}/{{ formatCount(currentResult?.total_count) }}</small>
                                </div>
                                <button v-for="(row, index) in sampleRows" :key="sampleKey(row, index)"
                                    :class="{ active: selectedRowIndex === index }" @click="selectedRowIndex = index">
                                    <span>#{{ index + 1 }}</span>
                                    <strong>{{ sampleTitle(row, index) }}</strong>
                                    <i v-if="rowChanged(row, index)" :title="local('Changed')"></i>
                                </button>
                            </aside>

                            <sample-inspector :before-sample="previousSample" :after-sample="currentSample"
                                :before-title="previousOperatorTitle" :after-title="selectedOperatorTitle"
                                :theme="theme" />
                        </div>
                    </section>
                </template>
            </main>
        </div>

        <div v-if="credentialOpen" class="credential-backdrop" @click.self="closeCredentialPanel">
            <section class="credential-dialog" role="dialog" aria-modal="true"
                :aria-label="local('Runtime credentials')">
                <div class="credential-dialog-heading">
                    <div>
                        <p class="eyebrow">AI4S RUNTIME</p>
                        <h2>{{ local('Runtime credentials') }}</h2>
                    </div>
                    <button class="dialog-close" :aria-label="local('Close')" @click="closeCredentialPanel">×</button>
                </div>

                <p class="credential-intro">
                    {{ local('Open-source installations start without credentials. Non-secret model settings are saved, while every API key must be entered again after a backend restart.') }}
                </p>

                <div class="credential-scroll">
                    <section class="credential-group">
                        <div class="credential-group-heading">
                            <div>
                                <p class="eyebrow">PDF / OCR</p>
                                <h3>MinerU</h3>
                            </div>
                            <span class="credential-pill" :class="{ configured: mineruConfigured }">
                                {{ mineruConfigured ? local('Ready') : local('Key required') }}
                            </span>
                        </div>

                        <form class="compact-credential-form" @submit.prevent="saveMineruCredential">
                            <input v-model="mineruKey" type="password" autocomplete="new-password" spellcheck="false"
                                :aria-label="local('MinerU API key')" :placeholder="local('MinerU API key')" />
                            <button v-if="mineruConfigured" type="button" class="clear-credential"
                                :disabled="credentialSaving" @click="clearMineruCredential">
                                {{ local('Clear') }}
                            </button>
                            <button type="submit" class="save-credential"
                                :disabled="credentialSaving || !mineruKey.trim()">
                                {{ local('Save key') }}
                            </button>
                        </form>
                    </section>

                    <section class="credential-group">
                        <div class="credential-group-heading">
                            <div>
                                <p class="eyebrow">LLM</p>
                                <h3>{{ local('Model servings') }}</h3>
                            </div>
                            <button class="add-serving" @click="showServingForm = !showServingForm">
                                {{ showServingForm ? local('Cancel') : local('Add serving') }}
                            </button>
                        </div>

                        <div v-if="!servings.length && !showServingForm" class="credential-empty">
                            <strong>{{ local('No model serving configured') }}</strong>
                            <p>{{ local('Add an API-compatible model endpoint before running an LLM operator.') }}</p>
                            <button @click="showServingForm = true">{{ local('Add first serving') }}</button>
                        </div>

                        <form v-if="showServingForm" class="serving-create-form" @submit.prevent="createServing">
                            <div class="serving-form-grid">
                                <label>
                                    <span>{{ local('Serving name') }}</span>
                                    <input v-model="servingForm.name" required :placeholder="local('Scientific model')" />
                                </label>
                                <label>
                                    <span>{{ local('Model name') }}</span>
                                    <input v-model="servingForm.model_name" required placeholder="gpt-4o" />
                                </label>
                                <label class="wide">
                                    <span>{{ local('API URL') }}</span>
                                    <input v-model="servingForm.api_url" required type="url"
                                        placeholder="https://provider.example/v1/chat/completions" />
                                </label>
                                <label>
                                    <span>{{ local('API key') }}</span>
                                    <input v-model="servingForm.api_key" required type="password"
                                        autocomplete="new-password" spellcheck="false" />
                                </label>
                                <label>
                                    <span>{{ local('Concurrency') }}</span>
                                    <input v-model.number="servingForm.max_workers" required type="number" min="1" max="512" />
                                </label>
                            </div>
                            <div class="credential-actions">
                                <button type="submit" class="save-credential"
                                    :disabled="credentialSaving || !servingForm.api_key.trim()">
                                    {{ local('Create serving') }}
                                </button>
                            </div>
                        </form>

                        <article v-for="serving in servings" :key="serving.id" class="serving-card">
                            <div class="serving-card-heading">
                                <div>
                                    <strong>{{ serving.name }}</strong>
                                    <code>{{ serving.id }}</code>
                                </div>
                                <span class="credential-pill" :class="{ configured: serving.credential_configured }">
                                    {{ serving.credential_configured ? local('Ready') : local('Key required') }}
                                </span>
                            </div>
                            <p>{{ servingParam(serving, 'model_name') }} · {{ servingParam(serving, 'api_url') }}</p>
                            <form class="compact-credential-form" @submit.prevent="saveServingCredential(serving)">
                                <input v-model="servingKeys[serving.id]" type="password" autocomplete="new-password"
                                    spellcheck="false" :aria-label="local('API key')" :placeholder="local('Enter API key for this session')" />
                                <button v-if="serving.credential_configured" type="button" class="clear-credential"
                                    :disabled="credentialSaving" @click="clearServingCredential(serving)">
                                    {{ local('Clear') }}
                                </button>
                                <button type="submit" class="save-credential"
                                    :disabled="credentialSaving || !String(servingKeys[serving.id] || '').trim()">
                                    {{ local('Save key') }}
                                </button>
                            </form>
                            <div class="serving-card-actions">
                                <span :class="{ error: servingMessages[serving.id]?.error }">
                                    {{ servingMessages[serving.id]?.text || '' }}
                                </span>
                                <button :disabled="credentialSaving || !serving.credential_configured"
                                    @click="testServing(serving)">{{ local('Test') }}</button>
                                <button class="danger" :disabled="credentialSaving"
                                    @click="deleteServing(serving)">{{ local('Delete configuration') }}</button>
                            </div>
                        </article>
                    </section>
                </div>

                <footer class="credential-footer">
                    <p>{{ local('Keys stay in process memory only. Use a trusted local or HTTPS connection.') }}</p>
                    <p v-if="credentialError" class="credential-error">{{ credentialError }}</p>
                </footer>
            </section>
        </div>
    </div>
</template>

<script>
import { mapState } from 'pinia'
import { useAppConfig } from '@/stores/appConfig'
import { useTheme } from '@/stores/theme'
import axios from '@/axios/config'

import logo from '@/assets/logo/logo.png'
import sampleInspector from '@/components/manage/mainFlow/panels/execResultPanel/preview/sampleInspector.vue'

const SAMPLE_LIMIT = 30
const REFRESH_INTERVAL = 4000
const ID_FIELDS = ['sample_id', 'source_id', 'id', '_id']

export default {
    name: 'OperatorResultViewer',
    components: { sampleInspector },
    data() {
        return {
            logo,
            tasks: [],
            pipelines: [],
            currentTask: null,
            selectedTaskId: null,
            selectedStep: null,
            selectedRowIndex: 0,
            currentResult: null,
            previousResult: null,
            overviewLoading: false,
            resultLoading: false,
            resultError: '',
            refreshTimer: null,
            requestVersion: 0,
            credentialOpen: false,
            credentialSaving: false,
            credentialError: '',
            mineruConfigured: false,
            mineruKey: '',
            servings: [],
            servingKeys: {},
            servingMessages: {},
            showServingForm: false,
            servingForm: {
                name: '',
                api_url: '',
                model_name: '',
                api_key: '',
                max_workers: 10
            }
        }
    },
    computed: {
        ...mapState(useAppConfig, ['local']),
        ...mapState(useTheme, ['theme']),
        credentialConfiguredCount() {
            return Number(this.mineruConfigured)
                + this.servings.filter((serving) => serving.credential_configured).length
        },
        steps() {
            const detail = this.currentTask?.operators_detail || this.currentTask?.output?.operators_detail || {}
            return Object.values(detail).sort((a, b) => a.index - b.index)
        },
        completedSteps() {
            return this.steps.filter((step) => step.status === 'completed').length
        },
        currentPipelineName() {
            return this.taskPipelineName(this.currentTask)
        },
        selectedStepInfo() {
            return this.steps.find((step) => step.index === this.selectedStep) || null
        },
        selectedOperatorTitle() {
            if (!this.selectedStepInfo) return this.local('Select an operator')
            return `${this.local('Processing Step')} ${this.selectedStep + 1} · ${this.selectedStepInfo.name}`
        },
        previousOperatorTitle() {
            if (this.selectedStep === 0) return this.local('Source data')
            const previous = this.steps.find((step) => step.index === this.selectedStep - 1)
            return previous ? `${this.local('Processing Step')} ${previous.index + 1} · ${previous.name}` : this.local('Previous operator')
        },
        sampleRows() {
            return Array.isArray(this.currentResult?.sample_data) ? this.currentResult.sample_data : []
        },
        currentSample() {
            return this.sampleRows[this.selectedRowIndex] || null
        },
        previousSample() {
            return this.findPreviousSample(this.currentSample, this.selectedRowIndex)
        },
        currentTotal() {
            const resultCount = Number(this.currentResult?.total_count)
            if (Number.isFinite(resultCount) && resultCount > 0) return resultCount.toLocaleString()
            const stepCount = Number(this.selectedStepInfo?.sample_count)
            return Number.isFinite(stepCount) ? stepCount.toLocaleString() : '—'
        },
        retentionRate() {
            const current = Number(this.currentResult?.total_count)
            const previous = Number(this.previousResult?.total_count)
            if (!Number.isFinite(current) || !Number.isFinite(previous) || previous <= 0) return '—'
            return `${Math.round((current / previous) * 1000) / 10}%`
        }
    },
    async mounted() {
        await Promise.all([this.loadOverview(false), this.loadCredentialStatus()])
        this.refreshTimer = window.setInterval(() => this.loadOverview(true), REFRESH_INTERVAL)
    },
    beforeUnmount() {
        window.clearInterval(this.refreshTimer)
    },
    methods: {
        apiUrl(path) {
            const base = (axios.defaults.baseURL || '').replace(/\/+$/, '')
            return `${base}${path}`
        },
        async apiRequest(path, method = 'GET', body = null) {
            const response = await fetch(this.apiUrl(path), {
                method,
                headers: body ? { 'Content-Type': 'application/json' } : undefined,
                body: body ? JSON.stringify(body) : undefined,
                cache: 'no-store'
            })
            const payload = await response.json().catch(() => null)
            if (!response.ok || payload?.code !== 200) {
                const detail = payload?.detail
                const detailMessage = typeof detail === 'string' ? detail : detail?.message
                throw new Error(detailMessage || payload?.message || this.local('Unable to update credential'))
            }
            return payload.data
        },
        async loadCredentialStatus() {
            try {
                const [status, servings] = await Promise.all([
                    this.apiRequest('/api/v1/runtime-credentials/mineru'),
                    this.apiRequest('/api/v1/serving/')
                ])
                this.mineruConfigured = Boolean(status?.configured)
                this.servings = Array.isArray(servings) ? servings : []
                for (const serving of this.servings) {
                    if (!(serving.id in this.servingKeys)) this.servingKeys[serving.id] = ''
                }
            } catch (error) {
                this.credentialError = error?.message || this.local('Unable to load credentials')
            }
        },
        openCredentialPanel() {
            this.mineruKey = ''
            this.servingKeys = {}
            this.credentialError = ''
            this.credentialOpen = true
            this.loadCredentialStatus()
        },
        closeCredentialPanel() {
            if (this.credentialSaving) return
            this.mineruKey = ''
            this.servingKeys = {}
            this.servingForm.api_key = ''
            this.credentialError = ''
            this.credentialOpen = false
        },
        async saveMineruCredential() {
            if (!this.mineruKey.trim() || this.credentialSaving) return
            this.credentialSaving = true
            this.credentialError = ''
            try {
                const status = await this.apiRequest(
                    '/api/v1/runtime-credentials/mineru',
                    'PUT',
                    { api_key: this.mineruKey }
                )
                this.mineruConfigured = Boolean(status?.configured)
                this.mineruKey = ''
            } catch (error) {
                this.credentialError = error?.message || this.local('Unable to update credential')
            } finally {
                this.credentialSaving = false
            }
        },
        async clearMineruCredential() {
            if (this.credentialSaving) return
            this.credentialSaving = true
            this.credentialError = ''
            try {
                const status = await this.apiRequest('/api/v1/runtime-credentials/mineru', 'DELETE')
                this.mineruConfigured = Boolean(status?.configured)
                this.mineruKey = ''
            } catch (error) {
                this.credentialError = error?.message || this.local('Unable to update credential')
            } finally {
                this.credentialSaving = false
            }
        },
        servingParam(serving, name) {
            const param = (serving?.params || []).find((item) => item.name === name)
            return param?.value ?? param?.default_value ?? '—'
        },
        resetServingForm() {
            this.servingForm = {
                name: '',
                api_url: '',
                model_name: '',
                api_key: '',
                max_workers: 10
            }
        },
        async createServing() {
            if (this.credentialSaving || !this.servingForm.api_key.trim()) return
            this.credentialSaving = true
            this.credentialError = ''
            try {
                const query = new URLSearchParams({
                    name: this.servingForm.name.trim(),
                    cls_name: 'APILLMServing_request'
                })
                await this.apiRequest(`/api/v1/serving/?${query.toString()}`, 'POST', [
                    { name: 'api_url', value: this.servingForm.api_url.trim() },
                    { name: 'api_key', value: this.servingForm.api_key },
                    { name: 'model_name', value: this.servingForm.model_name.trim() },
                    { name: 'max_workers', value: Number(this.servingForm.max_workers) }
                ])
                this.resetServingForm()
                this.showServingForm = false
                await this.loadCredentialStatus()
            } catch (error) {
                this.credentialError = error?.message || this.local('Unable to create serving')
            } finally {
                this.credentialSaving = false
            }
        },
        async saveServingCredential(serving) {
            const apiKey = String(this.servingKeys[serving.id] || '').trim()
            if (!apiKey || this.credentialSaving) return
            this.credentialSaving = true
            this.servingMessages[serving.id] = null
            try {
                const status = await this.apiRequest(
                    `/api/v1/runtime-credentials/serving/${encodeURIComponent(serving.id)}`,
                    'PUT',
                    { api_key: apiKey }
                )
                serving.credential_configured = Boolean(status?.configured)
                this.servingKeys[serving.id] = ''
                this.servingMessages[serving.id] = { text: this.local('Key saved for this session'), error: false }
            } catch (error) {
                this.servingMessages[serving.id] = {
                    text: error?.message || this.local('Unable to update credential'),
                    error: true
                }
            } finally {
                this.credentialSaving = false
            }
        },
        async clearServingCredential(serving) {
            if (this.credentialSaving) return
            this.credentialSaving = true
            try {
                const status = await this.apiRequest(
                    `/api/v1/runtime-credentials/serving/${encodeURIComponent(serving.id)}`,
                    'DELETE'
                )
                serving.credential_configured = Boolean(status?.configured)
                this.servingKeys[serving.id] = ''
                this.servingMessages[serving.id] = { text: this.local('Credential cleared'), error: false }
            } catch (error) {
                this.servingMessages[serving.id] = {
                    text: error?.message || this.local('Unable to update credential'),
                    error: true
                }
            } finally {
                this.credentialSaving = false
            }
        },
        async testServing(serving) {
            if (this.credentialSaving || !serving.credential_configured) return
            this.credentialSaving = true
            this.servingMessages[serving.id] = { text: this.local('Testing connection'), error: false }
            try {
                await this.apiRequest(
                    `/api/v1/serving/${encodeURIComponent(serving.id)}/test`,
                    'POST',
                    { prompt: 'Reply with OK.' }
                )
                this.servingMessages[serving.id] = { text: this.local('Connection successful'), error: false }
            } catch (error) {
                this.servingMessages[serving.id] = {
                    text: error?.message || this.local('Connection failed'),
                    error: true
                }
            } finally {
                this.credentialSaving = false
            }
        },
        async deleteServing(serving) {
            if (this.credentialSaving) return
            if (!window.confirm(this.local('Delete this serving configuration?'))) return
            this.credentialSaving = true
            this.credentialError = ''
            try {
                await this.apiRequest(`/api/v1/serving/${encodeURIComponent(serving.id)}`, 'DELETE')
                delete this.servingKeys[serving.id]
                delete this.servingMessages[serving.id]
                await this.loadCredentialStatus()
            } catch (error) {
                this.credentialError = error?.message || this.local('Unable to delete serving')
            } finally {
                this.credentialSaving = false
            }
        },
        async loadOverview(silent = false) {
            if (!silent) this.overviewLoading = true
            try {
                const [taskResponse, pipelineResponse] = await Promise.all([
                    this.$api.tasks.list_executions(),
                    this.$api.pipelines.list_pipelines()
                ])
                if (pipelineResponse.code === 200) this.pipelines = pipelineResponse.data || []
                if (taskResponse.code !== 200) return

                this.tasks = [...(taskResponse.data || [])].sort((a, b) => {
                    const left = new Date(a.completed_at || a.started_at || 0).getTime()
                    const right = new Date(b.completed_at || b.started_at || 0).getTime()
                    return right - left
                })

                const selected = this.tasks.find((task) => task.task_id === this.selectedTaskId)
                if (!selected && this.tasks.length) {
                    await this.selectTask(this.tasks[0])
                } else if (selected && ['queued', 'running'].includes(selected.status)) {
                    await this.refreshCurrentTask(selected)
                }
            } catch (error) {
                if (!silent) this.resultError = error?.message || this.local('Unable to load runs')
            } finally {
                this.overviewLoading = false
            }
        },
        async selectTask(task) {
            if (!task?.task_id) return
            this.selectedTaskId = task.task_id
            this.currentTask = task
            this.currentResult = null
            this.previousResult = null
            this.selectedRowIndex = 0
            this.resultError = ''

            try {
                const response = await this.$api.tasks.get_execution_status(task.task_id)
                if (response.code === 200) this.currentTask = { ...task, ...response.data }
            } catch (_) {
                // The execution list already carries enough information for completed runs.
            }

            const target = this.steps.find((step) => step.status === 'running')
                || this.steps.filter((step) => step.status === 'completed').at(-1)
                || this.steps.find((step) => step.status === 'failed')
                || this.steps.at(-1)
            if (target) await this.selectStep(target.index)
            else this.selectedStep = null
        },
        async refreshCurrentTask(task) {
            try {
                const response = await this.$api.tasks.get_execution_status(task.task_id)
                if (response.code !== 200) return
                this.currentTask = { ...task, ...response.data }
                const running = this.steps.find((step) => step.status === 'running')
                const latest = running || this.steps.filter((step) => step.status === 'completed').at(-1)
                if (latest && latest.index !== this.selectedStep) await this.selectStep(latest.index)
            } catch (_) {
                // Keep the last visible state while the next auto refresh retries.
            }
        },
        async selectStep(step) {
            if (!this.selectedTaskId || !Number.isInteger(step)) return
            const requestVersion = ++this.requestVersion
            this.selectedStep = step
            this.selectedRowIndex = 0
            this.resultLoading = true
            this.resultError = ''

            try {
                const requests = [this.$api.tasks.get_task_result(this.selectedTaskId, step, SAMPLE_LIMIT)]
                if (step > 0) requests.push(this.$api.tasks.get_task_result(this.selectedTaskId, step - 1, SAMPLE_LIMIT))
                const [currentResponse, previousResponse] = await Promise.all(requests)
                if (requestVersion !== this.requestVersion) return
                if (currentResponse.code !== 200) throw new Error(currentResponse.message || this.local('Unable to load this result'))

                const [current, previous] = await Promise.all([
                    this.ensureStepSamples(currentResponse.data, this.selectedTaskId, step),
                    previousResponse?.code === 200
                        ? this.ensureStepSamples(previousResponse.data, this.selectedTaskId, step - 1)
                        : null
                ])
                if (requestVersion !== this.requestVersion) return
                this.currentResult = current
                this.previousResult = previous
            } catch (error) {
                if (requestVersion !== this.requestVersion) return
                this.resultError = error?.message || this.local('Unable to load this result')
            } finally {
                if (requestVersion === this.requestVersion) this.resultLoading = false
            }
        },
        async ensureStepSamples(result, taskId, step) {
            if (!result || step < 0) return result
            if (Array.isArray(result.sample_data) && result.sample_data.length) return result
            const detail = Object.values(result.operators_detail || {}).find((item) => item.index === step)
            const expectedCount = Number(detail?.sample_count)
            if (!Number.isFinite(expectedCount) || expectedCount <= 0) return result

            try {
                const response = await fetch(this.stepDownloadUrl(taskId, step))
                if (!response.ok) return result
                const contentType = String(response.headers.get('content-type') || '').toLowerCase()
                if (!contentType.includes('jsonl') && !contentType.includes('ndjson')) return result
                const text = await response.text()
                const lines = text.split(/\r?\n/).filter((line) => line.trim())
                const sampleData = []
                for (const line of lines.slice(0, SAMPLE_LIMIT)) {
                    try {
                        sampleData.push(JSON.parse(line))
                    } catch (_) {
                        // Ignore malformed rows without hiding valid scientific records.
                    }
                }
                return {
                    ...result,
                    sample_data: sampleData,
                    sample_count: sampleData.length,
                    total_count: lines.length,
                    file_exists: true
                }
            } catch (_) {
                return result
            }
        },
        findPreviousSample(row, index) {
            const rows = Array.isArray(this.previousResult?.sample_data) ? this.previousResult.sample_data : []
            if (!row || !rows.length) return null
            for (const field of ID_FIELDS) {
                if (row[field] === null || row[field] === undefined) continue
                const match = rows.find((candidate) => candidate?.[field] === row[field])
                if (match) return match
            }
            return rows[index] || null
        },
        rowChanged(row, index) {
            const previous = this.findPreviousSample(row, index)
            if (!previous) return this.selectedStep === 0
            const keys = new Set([...Object.keys(previous), ...Object.keys(row || {})])
            return [...keys].some((key) => this.stableValue(previous[key]) !== this.stableValue(row?.[key]))
        },
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
        sampleKey(row, index) {
            for (const field of ID_FIELDS) {
                if (row?.[field] !== null && row?.[field] !== undefined) return `${field}-${row[field]}-${index}`
            }
            return index
        },
        sampleTitle(row, index) {
            for (const field of [...ID_FIELDS, 'source', 'file_name', 'question', 'text', 'raw_content']) {
                if (row?.[field] !== null && row?.[field] !== undefined && row?.[field] !== '') {
                    const value = String(row[field]).replace(/\s+/g, ' ')
                    return value.length > 52 ? `${value.slice(0, 49)}…` : value
                }
            }
            return `${this.local('Sample')} ${index + 1}`
        },
        taskPipelineName(task) {
            if (!task) return this.local('Pipeline run')
            const pipeline = this.pipelines.find((item) => item.id === task.pipeline_id)
            return pipeline?.name || task.pipeline_config?.name || this.local('Pipeline run')
        },
        statusLabel(status) {
            const labels = {
                completed: this.local('Completed'),
                failed: this.local('Failed'),
                running: this.local('Running'),
                queued: this.local('Queued'),
                cancelled: this.local('Cancelled'),
                initialized: this.local('Ready'),
                initializing: this.local('Initializing')
            }
            return labels[status] || status || this.local('Unknown')
        },
        statusClass(status) {
            return `status-${status || 'unknown'}`
        },
        formatDate(value) {
            if (!value) return this.local('Time unavailable')
            const date = new Date(value)
            if (Number.isNaN(date.getTime())) return value
            return new Intl.DateTimeFormat(undefined, {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }).format(date)
        },
        formatCount(value) {
            const count = Number(value)
            return Number.isFinite(count) ? count.toLocaleString() : '—'
        },
        stepDownloadUrl(taskId, step) {
            const base = (axios.defaults.baseURL || '').replace(/\/+$/, '')
            return `${base}/api/v1/tasks/execution/${encodeURIComponent(taskId)}/download?step=${step}`
        },
        downloadStep() {
            if (!this.selectedTaskId || this.selectedStep === null) return
            window.open(this.stepDownloadUrl(this.selectedTaskId, this.selectedStep), '_blank')
        }
    }
}
</script>

<style lang="scss">
.result-viewer {
    --page: #f4f6fa;
    --surface: #ffffff;
    --surface-soft: #f8f9fc;
    --text: #172033;
    --muted: #71798a;
    --border: rgba(77, 91, 120, 0.14);
    --accent: #4f63d8;
    --accent-soft: rgba(79, 99, 216, 0.1);

    width: 100vw;
    height: 100vh;
    color: var(--text);
    background: var(--page);
    display: flex;
    flex-direction: column;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;

    &.dark {
        --page: #171a20;
        --surface: #232730;
        --surface-soft: #1e222a;
        --text: #f1f3f8;
        --muted: #a7aebb;
        --border: rgba(220, 225, 235, 0.11);
        --accent: #93a1ff;
        --accent-soft: rgba(147, 161, 255, 0.13);
    }

    button {
        font: inherit;
    }

    .viewer-header {
        height: 72px;
        padding: 0 24px;
        background: var(--surface);
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-shrink: 0;
    }

    .brand-block {
        display: flex;
        align-items: center;
        gap: 11px;

        img {
            width: 34px;
            height: 34px;
            object-fit: contain;
        }

        h1 {
            margin-top: 2px;
            font-size: 18px;
        }
    }

    .eyebrow {
        color: var(--accent);
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .header-controls {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .auto-refresh {
        color: var(--muted);
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;

        i {
            width: 7px;
            height: 7px;
            background: #9ca3af;
            border-radius: 50%;
        }

        &.active i {
            background: #17a673;
            box-shadow: 0 0 0 3px rgba(23, 166, 115, 0.12);
        }
    }

    .credential-button,
    .icon-button,
    .download-button {
        color: var(--accent);
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        cursor: pointer;
    }

    .credential-button {
        min-height: 34px;
        padding: 0 11px;
        display: flex;
        align-items: center;
        gap: 7px;
        font-size: 10px;

        > span {
            min-width: 18px;
            height: 18px;
            padding: 0 5px;
            color: var(--muted);
            background: var(--surface-soft);
            border-radius: 999px;
            display: grid;
            place-items: center;
            font-size: 9px;
        }

        i {
            width: 7px;
            height: 7px;
            background: #d77b12;
            border-radius: 50%;
        }

        &.configured i {
            background: #17a673;
            box-shadow: 0 0 0 3px rgba(23, 166, 115, 0.12);
        }
    }

    .icon-button {
        width: 34px;
        height: 34px;
        font-size: 19px;
    }

    .viewer-body {
        min-height: 0;
        flex: 1;
        display: grid;
        grid-template-columns: 300px minmax(0, 1fr);
    }

    .run-sidebar {
        min-height: 0;
        padding: 18px 14px;
        background: var(--surface);
        border-right: 1px solid var(--border);
        display: flex;
        flex-direction: column;
    }

    .sidebar-heading,
    .section-heading,
    .run-overview {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 14px;
    }

    .sidebar-heading {
        padding: 0 5px 14px;

        h2 {
            margin-top: 3px;
            font-size: 14px;
        }

        > span {
            min-width: 26px;
            height: 26px;
            padding: 0 7px;
            color: var(--muted);
            background: var(--surface-soft);
            border-radius: 999px;
            display: grid;
            place-items: center;
            font-size: 10px;
        }
    }

    .run-list {
        min-height: 0;
        display: flex;
        flex-direction: column;
        gap: 7px;
        overflow-y: auto;
    }

    .run-card {
        width: 100%;
        min-height: 92px;
        padding: 11px;
        color: var(--text);
        background: transparent;
        border: 1px solid var(--border);
        border-radius: 10px;
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 4px 8px;
        text-align: left;
        cursor: pointer;

        &:hover,
        &.active {
            background: var(--accent-soft);
            border-color: rgba(79, 99, 216, 0.32);
        }

        &.active {
            box-shadow: inset 3px 0 var(--accent);
        }

        strong {
            grid-column: 1 / 3;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 12px;
        }

        small,
        code {
            color: var(--muted);
            font-size: 9px;
        }

        code {
            align-self: end;
            text-align: right;
        }
    }

    .run-status,
    .large-status {
        width: fit-content;
        padding: 3px 7px;
        color: #775c0a;
        background: rgba(234, 179, 8, 0.13);
        border-radius: 999px;
        font-size: 9px;
        font-weight: 700;

        &.status-completed {
            color: #117454;
            background: rgba(17, 116, 84, 0.12);
        }

        &.status-failed,
        &.status-cancelled {
            color: #b43b45;
            background: rgba(180, 59, 69, 0.11);
        }
    }

    .result-main {
        min-width: 0;
        padding: 20px;
        overflow-y: auto;
    }

    .run-overview,
    .operator-section,
    .sample-section {
        max-width: 1500px;
        margin: 0 auto 14px;
        padding: 17px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(22, 31, 54, 0.035);
    }

    .run-overview {
        h2 {
            margin: 4px 0;
            font-size: 20px;
        }
    }

    .run-description {
        color: var(--muted);
        font-size: 10px;

        span {
            margin: 0 6px;
        }
    }

    .run-summary {
        display: flex;
        align-items: center;
        gap: 22px;

        div {
            display: flex;
            flex-direction: column;
            align-items: flex-end;

            strong {
                font-size: 18px;
            }

            span {
                color: var(--muted);
                font-size: 9px;
            }
        }

        .large-status {
            padding: 6px 10px;
            font-size: 10px;
        }
    }

    .section-heading {
        margin-bottom: 13px;

        h3 {
            margin-top: 3px;
            font-size: 14px;
        }
    }

    .download-button {
        min-height: 34px;
        padding: 0 12px;
        font-size: 10px;
    }

    .operator-track {
        display: flex;
        gap: 9px;
        padding: 2px 1px 7px;
        overflow-x: auto;
    }

    .operator-card {
        position: relative;
        min-width: 210px;
        min-height: 64px;
        padding: 10px;
        color: var(--text);
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 9px;
        display: grid;
        grid-template-columns: 30px 1fr;
        grid-template-rows: 1fr auto;
        gap: 2px 7px;
        text-align: left;
        cursor: pointer;

        &::after {
            position: absolute;
            top: 50%;
            left: calc(100% + 1px);
            width: 8px;
            height: 1px;
            background: var(--border);
            content: '';
        }

        &:last-child::after {
            display: none;
        }

        &:hover,
        &.active {
            border-color: var(--accent);
            box-shadow: 0 0 0 2px var(--accent-soft);
        }
    }

    .operator-index {
        grid-row: 1 / 3;
        width: 27px;
        height: 27px;
        color: var(--accent);
        background: var(--accent-soft);
        border-radius: 50%;
        display: grid;
        place-items: center;
        font-size: 10px;
        font-weight: 800;
    }

    .operator-copy {
        min-width: 0;
        display: flex;
        flex-direction: column;

        strong,
        small {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        strong {
            font-size: 11px;
        }

        small {
            margin-top: 3px;
            color: var(--muted);
            font-size: 9px;
        }
    }

    .operator-status {
        color: var(--muted);
        font-size: 9px;
    }

    .result-metrics {
        display: flex;
        gap: 6px;

        span {
            padding: 5px 8px;
            color: var(--muted);
            background: var(--surface-soft);
            border-radius: 999px;
            font-size: 9px;
        }
    }

    .sample-layout {
        min-height: 430px;
        display: grid;
        grid-template-columns: 250px minmax(0, 1fr);
        gap: 11px;
    }

    .sample-list {
        max-height: 580px;
        padding: 5px;
        background: var(--surface-soft);
        border: 1px solid var(--border);
        border-radius: 9px;
        overflow-y: auto;

        .sample-list-heading {
            min-height: 34px;
            padding: 5px 7px;
            color: var(--muted);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 9px;
            font-weight: 700;
            text-transform: uppercase;
        }

        button {
            width: 100%;
            min-height: 43px;
            padding: 7px;
            color: var(--text);
            background: transparent;
            border: 0;
            border-radius: 7px;
            display: grid;
            grid-template-columns: 25px 1fr 7px;
            gap: 5px;
            align-items: center;
            text-align: left;
            cursor: pointer;

            &:hover,
            &.active {
                background: var(--surface);
            }

            &.active {
                box-shadow: inset 3px 0 var(--accent);
            }

            span {
                color: var(--muted);
                font-size: 9px;
            }

            strong {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                font-size: 10px;
                font-weight: 500;
            }

            i {
                width: 6px;
                height: 6px;
                background: #d77b12;
                border-radius: 50%;
            }
        }
    }

    .result-state,
    .main-empty,
    .sidebar-empty,
    .inline-empty {
        color: var(--muted);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }

    .result-state {
        min-height: 340px;
        gap: 8px;
        font-size: 11px;

        &.error strong {
            color: #b43b45;
        }
    }

    .main-empty {
        height: 100%;
        gap: 8px;

        .empty-symbol {
            color: var(--accent);
            font-size: 50px;
        }

        h2 {
            color: var(--text);
            font-size: 18px;
        }

        p {
            max-width: 470px;
            font-size: 11px;
            line-height: 1.6;
        }
    }

    .sidebar-empty {
        flex: 1;
        gap: 8px;
        padding: 18px;

        strong {
            color: var(--text);
            font-size: 12px;
        }

        p {
            font-size: 10px;
            line-height: 1.6;
        }
    }

    .inline-empty {
        min-height: 80px;
        font-size: 11px;
    }

    .loading-ring {
        width: 18px;
        height: 18px;
        border: 2px solid var(--border);
        border-top-color: var(--accent);
        border-radius: 50%;
        animation: viewer-spin 0.75s linear infinite;
    }

    .credential-backdrop {
        position: fixed;
        z-index: 1000;
        inset: 0;
        padding: 24px;
        background: rgba(12, 17, 29, 0.48);
        display: grid;
        place-items: center;
        backdrop-filter: blur(3px);
    }

    .credential-dialog {
        width: min(720px, 100%);
        max-height: min(880px, calc(100vh - 48px));
        padding: 20px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        display: flex;
        flex-direction: column;
        box-shadow: 0 24px 70px rgba(8, 13, 25, 0.28);

        h2 {
            margin-top: 4px;
            font-size: 18px;
        }

        input {
            width: 100%;
            height: 38px;
            padding: 0 11px;
            color: var(--text);
            background: var(--surface-soft);
            border: 1px solid var(--border);
            border-radius: 8px;
            outline: none;

            &:focus {
                border-color: var(--accent);
                box-shadow: 0 0 0 3px var(--accent-soft);
            }
        }
    }

    .credential-dialog-heading {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 16px;
    }

    .dialog-close {
        width: 30px;
        height: 30px;
        color: var(--muted);
        background: transparent;
        border: 0;
        border-radius: 7px;
        cursor: pointer;
        font-size: 21px;

        &:hover {
            color: var(--text);
            background: var(--surface-soft);
        }
    }

    .credential-intro,
    .credential-footer {
        color: var(--muted);
        font-size: 10px;
        line-height: 1.55;
    }

    .credential-intro {
        margin-top: 12px;
    }

    .credential-scroll {
        min-height: 0;
        margin: 16px -4px 0 0;
        padding-right: 4px;
        overflow-y: auto;
    }

    .credential-group {
        padding: 14px;
        background: var(--surface-soft);
        border: 1px solid var(--border);
        border-radius: 11px;

        + .credential-group {
            margin-top: 10px;
        }
    }

    .credential-group-heading,
    .serving-card-heading {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;

        h3 {
            margin-top: 3px;
            font-size: 13px;
        }
    }

    .credential-pill {
        padding: 4px 8px;
        color: #9a6410;
        background: rgba(215, 123, 18, 0.1);
        border-radius: 999px;
        font-size: 9px;
        font-weight: 700;

        &.configured {
            color: #117454;
            background: rgba(23, 166, 115, 0.1);
        }
    }

    .compact-credential-form {
        margin-top: 12px;
        display: grid;
        grid-template-columns: minmax(140px, 1fr) auto auto;
        gap: 7px;

        button {
            min-height: 38px;
            padding: 0 11px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 10px;

            &:disabled {
                cursor: not-allowed;
                opacity: 0.5;
            }
        }
    }

    .save-credential,
    .add-serving,
    .credential-empty button {
        color: #fff;
        background: var(--accent);
        border: 1px solid var(--accent);
    }

    .clear-credential {
        color: #b43b45;
        background: transparent;
        border: 1px solid rgba(180, 59, 69, 0.25);
    }

    .add-serving {
        min-height: 30px;
        padding: 0 10px;
        border-radius: 7px;
        cursor: pointer;
        font-size: 9px;
    }

    .credential-empty {
        min-height: 120px;
        margin-top: 12px;
        padding: 16px;
        border: 1px dashed var(--border);
        border-radius: 9px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 6px;
        text-align: center;

        strong {
            font-size: 11px;
        }

        p {
            color: var(--muted);
            font-size: 9px;
        }

        button {
            min-height: 30px;
            margin-top: 4px;
            padding: 0 10px;
            border-radius: 7px;
            cursor: pointer;
            font-size: 9px;
        }
    }

    .serving-create-form {
        margin-top: 12px;
        padding: 12px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 9px;
    }

    .serving-form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;

        label {
            display: flex;
            flex-direction: column;
            gap: 5px;

            &.wide {
                grid-column: 1 / 3;
            }

            span {
                color: var(--muted);
                font-size: 9px;
                font-weight: 700;
            }
        }
    }

    .serving-card {
        margin-top: 10px;
        padding: 12px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 9px;

        > p {
            margin-top: 7px;
            color: var(--muted);
            overflow-wrap: anywhere;
            font-size: 9px;
        }
    }

    .serving-card-heading {
        > div {
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 3px;
        }

        strong {
            font-size: 11px;
        }

        code {
            color: var(--muted);
            font-size: 8px;
        }
    }

    .serving-card-actions {
        min-height: 28px;
        margin-top: 7px;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 8px;

        span {
            margin-right: auto;
            color: #117454;
            font-size: 9px;

            &.error {
                color: #b43b45;
            }
        }

        button {
            padding: 0;
            color: var(--accent);
            background: transparent;
            border: 0;
            cursor: pointer;
            font-size: 9px;

            &.danger {
                color: #b43b45;
            }

            &:disabled {
                cursor: not-allowed;
                opacity: 0.45;
            }
        }
    }

    .credential-footer {
        padding-top: 12px;
        border-top: 1px solid var(--border);
    }

    .credential-error {
        margin-top: 5px;
        color: #b43b45;
        font-size: 9px;
        line-height: 1.5;
    }

    .credential-actions {
        margin-top: 10px;
        display: flex;
        justify-content: flex-end;
        gap: 8px;

        button {
            min-height: 36px;
            padding: 0 13px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 10px;

            &:disabled {
                cursor: not-allowed;
                opacity: 0.5;
            }
        }

    }
}

@keyframes viewer-spin {
    to {
        transform: rotate(360deg);
    }
}

@media (max-width: 900px) {
    .result-viewer {
        .credential-button {
            width: 34px;
            padding: 0;
            justify-content: center;
            font-size: 0;
        }

        .viewer-body {
            grid-template-columns: 230px minmax(0, 1fr);
        }

        .run-summary div {
            display: none;
        }

        .sample-layout {
            grid-template-columns: 180px minmax(0, 1fr);
        }
    }
}
</style>
