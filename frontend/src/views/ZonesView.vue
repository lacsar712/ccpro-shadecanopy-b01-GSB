<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api'

const list = ref([])
const greenhouses = ref([])
const error = ref('')
const editingId = ref(null)
const filterGreenhouseId = ref('')
const form = reactive({
  greenhouseId: '',
  zoneCode: '',
  cropName: '',
  status: 'idle',
})

const caps = ref([])
const capsError = ref('')
const capEditingId = ref(null)

function localDate(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const capForm = reactive({
  zoneId: '',
  workDate: localDate(),
  capPct: 80,
})

const statusLabel = { idle: '空闲', growing: '在种', fallow: '休耕' }

function formatErr(e, fallback = '保存失败') {
  const data = e.response?.data
  if (!data) return fallback
  if (typeof data === 'string') return data
  return Object.entries(data)
    .map(([k, v]) => `${k}: ${[].concat(v).join('；')}`)
    .join('；')
}

function resetForm() {
  editingId.value = null
  form.greenhouseId = greenhouses.value[0]?.id || ''
  form.zoneCode = ''
  form.cropName = ''
  form.status = 'idle'
}

async function loadGreenhouses() {
  const { data } = await api.get('/greenhouses/')
  greenhouses.value = data.results || data
  if (!form.greenhouseId && greenhouses.value.length) {
    form.greenhouseId = greenhouses.value[0].id
  }
}

async function load() {
  error.value = ''
  try {
    const params = {}
    if (filterGreenhouseId.value) params.greenhouseId = filterGreenhouseId.value
    const { data } = await api.get('/zones/', { params })
    list.value = data.results || data
    if (!capForm.zoneId && list.value.length) capForm.zoneId = list.value[0].id
  } catch {
    error.value = '加载分区失败'
  }
}

function edit(row) {
  editingId.value = row.id
  form.greenhouseId = row.greenhouseId
  form.zoneCode = row.zoneCode
  form.cropName = row.cropName
  form.status = row.status
}

async function save() {
  error.value = ''
  const payload = {
    greenhouseId: Number(form.greenhouseId),
    zoneCode: form.zoneCode,
    cropName: form.cropName,
    status: form.status,
  }
  try {
    if (editingId.value) {
      await api.put(`/zones/${editingId.value}/`, payload)
    } else {
      await api.post('/zones/', payload)
    }
    resetForm()
    await load()
  } catch (e) {
    error.value = JSON.stringify(e.response?.data || '保存失败')
  }
}

async function remove(id) {
  if (!confirm('确认删除该分区？')) return
  await api.delete(`/zones/${id}/`)
  await load()
}

async function loadCaps() {
  capsError.value = ''
  try {
    const { data } = await api.get('/humidity-caps/')
    caps.value = data.results || data
  } catch {
    capsError.value = '加载湿度上限账失败'
  }
}

function resetCapForm() {
  capEditingId.value = null
  capForm.zoneId = list.value[0]?.id || ''
  capForm.workDate = localDate()
  capForm.capPct = 80
}

function editCap(row) {
  capEditingId.value = row.id
  capForm.zoneId = row.zoneId
  capForm.workDate = row.workDate
  capForm.capPct = row.capPct
}

async function saveCap() {
  capsError.value = ''
  if (!Number.isInteger(Number(capForm.capPct)) || capForm.capPct < 40 || capForm.capPct > 100) {
    capsError.value = '湿度上限须为 40～100 的整数'
    return
  }
  const payload = {
    zoneId: Number(capForm.zoneId),
    workDate: capForm.workDate,
    capPct: Number(capForm.capPct),
  }
  try {
    if (capEditingId.value) {
      await api.put(`/humidity-caps/${capEditingId.value}/`, payload)
    } else {
      await api.post('/humidity-caps/', payload)
    }
    resetCapForm()
    await loadCaps()
    await load()
  } catch (e) {
    capsError.value = formatErr(e)
  }
}

async function removeCap(id) {
  if (!confirm('确认删除该湿度上限账？')) return
  await api.delete(`/humidity-caps/${id}/`)
  await loadCaps()
  await load()
}

onMounted(async () => {
  await loadGreenhouses()
  await load()
  await loadCaps()
})
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1>分区管理</h1>
        <p>同温室 zoneCode 唯一；状态 idle / growing / fallow</p>
      </div>
      <div class="actions">
        <select v-model="filterGreenhouseId" @change="load">
          <option value="">全部温室</option>
          <option v-for="g in greenhouses" :key="g.id" :value="g.id">{{ g.name }}</option>
        </select>
      </div>
    </div>

    <div class="panel">
      <h3 style="margin-top:0">{{ editingId ? '编辑分区' : '新建分区' }}</h3>
      <div class="form-grid">
        <label>
          温室
          <select v-model="form.greenhouseId">
            <option v-for="g in greenhouses" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </label>
        <label>分区编码<input v-model="form.zoneCode" required /></label>
        <label>作物<input v-model="form.cropName" /></label>
        <label>
          状态
          <select v-model="form.status">
            <option value="idle">空闲</option>
            <option value="growing">在种</option>
            <option value="fallow">休耕</option>
          </select>
        </label>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="actions" style="margin-top:12px">
        <button class="btn" @click="save">保存</button>
        <button v-if="editingId" class="btn ghost" @click="resetForm">取消编辑</button>
      </div>
    </div>

    <div class="panel">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>温室</th>
            <th>编码</th>
            <th>作物</th>
            <th>状态</th>
            <th>今日湿度上限</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in list" :key="row.id">
            <td>{{ row.id }}</td>
            <td>{{ row.greenhouseName }}</td>
            <td>{{ row.zoneCode }}</td>
            <td>{{ row.cropName || '—' }}</td>
            <td><span class="badge" :class="row.status">{{ statusLabel[row.status] || row.status }}</span></td>
            <td>{{ row.todayCapPct != null ? row.todayCapPct + '%' : '—' }}</td>
            <td class="actions">
              <button class="btn ghost" @click="edit(row)">编辑</button>
              <button class="btn danger" @click="remove(row.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="panel">
      <h3 style="margin-top:0">{{ capEditingId ? '编辑湿度上限账' : '新建湿度上限账' }}</h3>
      <p style="color:var(--muted);margin:0 0 12px">
        按东八区自然日生效，同区同日唯一；湿度上限为 40～100 的整数。气候记录湿度严格大于当日上限即被拒绝。
      </p>
      <div class="form-grid">
        <label>
          分区
          <select v-model="capForm.zoneId">
            <option v-for="z in list" :key="z.id" :value="z.id">
              {{ z.greenhouseName }} / {{ z.zoneCode }}
            </option>
          </select>
        </label>
        <label>作业日（东八区）<input v-model="capForm.workDate" type="date" /></label>
        <label>湿度上限 %<input v-model.number="capForm.capPct" type="number" min="40" max="100" step="1" /></label>
      </div>
      <p v-if="capsError" class="error">{{ capsError }}</p>
      <div class="actions" style="margin-top:12px">
        <button class="btn" @click="saveCap">保存上限</button>
        <button v-if="capEditingId" class="btn ghost" @click="resetCapForm">取消编辑</button>
      </div>

      <table style="margin-top:16px">
        <thead>
          <tr>
            <th>编号</th>
            <th>温室/分区</th>
            <th>作业日</th>
            <th>湿度上限</th>
            <th>设定人</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in caps" :key="row.id">
            <td>#{{ row.id }}</td>
            <td>{{ row.greenhouseName }} / {{ row.zoneCode }}</td>
            <td>{{ row.workDate }}</td>
            <td>{{ row.capPct }}%</td>
            <td>{{ row.setByName }}</td>
            <td class="actions">
              <button class="btn ghost" @click="editCap(row)">编辑</button>
              <button class="btn danger" @click="removeCap(row.id)">删除</button>
            </td>
          </tr>
          <tr v-if="!caps.length">
            <td colspan="6" style="color:var(--muted)">暂无湿度上限账</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
