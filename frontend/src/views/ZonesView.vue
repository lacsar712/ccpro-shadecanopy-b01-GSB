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

// 湿度上限账维护
const capPanel = ref(null)
const capList = ref([])
const capError = ref('')
const capEditingId = ref(null)
const capForm = reactive({
  zoneId: '',
  workDate: '',
  capPct: 80,
})

const statusLabel = { idle: '空闲', growing: '在种', fallow: '休耕' }

// 东八区（UTC+8）自然日：与后端归日口径一致，不随浏览器时区变化
function east8Today() {
  const now = new Date()
  const east8 = new Date(now.getTime() + (now.getTimezoneOffset() + 480) * 60000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${east8.getFullYear()}-${pad(east8.getMonth() + 1)}-${pad(east8.getDate())}`
}

function resetForm() {
  editingId.value = null
  form.greenhouseId = greenhouses.value[0]?.id || ''
  form.zoneCode = ''
  form.cropName = ''
  form.status = 'idle'
}

function resetCapForm(keepZone = true) {
  capEditingId.value = null
  if (!keepZone) capForm.zoneId = list.value[0]?.id || ''
  capForm.workDate = east8Today()
  capForm.capPct = 80
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
    if (!capForm.zoneId && list.value.length) {
      capForm.zoneId = list.value[0].id
    }
  } catch {
    error.value = '加载分区失败'
  }
}

async function loadCaps() {
  capError.value = ''
  if (!capForm.zoneId) {
    capList.value = []
    return
  }
  try {
    const { data } = await api.get('/humidity-caps/', {
      params: { zoneId: capForm.zoneId },
    })
    capList.value = data.results || data
  } catch {
    capError.value = '加载湿度上限失败'
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

function openCapPanel(row) {
  resetCapForm()
  capForm.zoneId = row.id
  loadCaps()
  capPanel.value?.scrollIntoView({ behavior: 'smooth' })
}

function editCap(row) {
  capEditingId.value = row.id
  capForm.workDate = row.workDate
  capForm.capPct = row.capPct
}

async function saveCap() {
  capError.value = ''
  if (!capForm.zoneId) {
    capError.value = '请先选择分区'
    return
  }
  const capPct = Number(capForm.capPct)
  if (!Number.isInteger(capPct) || capPct < 40 || capPct > 100) {
    capError.value = '湿度上限须为 40～100 的整数'
    return
  }
  if (!capForm.workDate) {
    capError.value = '请选择作业日'
    return
  }
  const payload = {
    zoneId: Number(capForm.zoneId),
    workDate: capForm.workDate,
    capPct,
  }
  try {
    // 同区同日唯一：编辑中走 PUT；否则同区同日已有上限账时改为更新该行
    const existing = capList.value.find(
      (c) => c.workDate === capForm.workDate && c.zoneId === Number(capForm.zoneId)
    )
    const targetId = capEditingId.value || existing?.id
    if (targetId) {
      await api.put(`/humidity-caps/${targetId}/`, payload)
    } else {
      await api.post('/humidity-caps/', payload)
    }
    resetCapForm()
    await loadCaps()
    await load()
  } catch (e) {
    capError.value = JSON.stringify(e.response?.data || '保存失败')
  }
}

async function removeCap(id) {
  if (!confirm('确认删除该湿度上限账？')) return
  await api.delete(`/humidity-caps/${id}/`)
  if (capEditingId.value === id) resetCapForm()
  await loadCaps()
  await load()
}

onMounted(async () => {
  resetCapForm(false)
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
        <p>同温室 zoneCode 唯一；湿度上限按东八区自然日归日</p>
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

    <div ref="capPanel" class="panel">
      <h3 style="margin-top:0">湿度上限账（按东八区自然日）</h3>
      <div class="form-grid">
        <label>
          分区
          <select v-model="capForm.zoneId" @change="resetCapForm(); loadCaps()">
            <option v-for="z in list" :key="z.id" :value="z.id">
              {{ z.greenhouseName }} / {{ z.zoneCode }}
            </option>
          </select>
        </label>
        <label>作业日<input v-model="capForm.workDate" type="date" /></label>
        <label>湿度上限 %（40～100 整数）<input v-model.number="capForm.capPct" type="number" step="1" min="40" max="100" /></label>
      </div>
      <p v-if="capError" class="error">{{ capError }}</p>
      <div class="actions" style="margin-top:12px">
        <button class="btn" @click="saveCap">{{ capEditingId ? '更新上限' : '保存上限' }}</button>
        <button v-if="capEditingId" class="btn ghost" @click="resetCapForm()">取消编辑</button>
      </div>

      <table style="margin-top:14px">
        <thead>
          <tr>
            <th>编号</th>
            <th>作业日</th>
            <th>湿度上限</th>
            <th>设定人</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in capList" :key="row.id">
            <td>#{{ row.id }}</td>
            <td>{{ row.workDate }}</td>
            <td>{{ row.capPct }}%</td>
            <td>{{ row.setByName || '—' }}</td>
            <td class="actions">
              <button class="btn ghost" @click="editCap(row)">编辑</button>
              <button class="btn danger" @click="removeCap(row.id)">删除</button>
            </td>
          </tr>
          <tr v-if="!capList.length">
            <td colspan="5" style="color:var(--muted)">该分区暂无湿度上限账</td>
          </tr>
        </tbody>
      </table>
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
              <button class="btn secondary" @click="openCapPanel(row)">上限</button>
              <button class="btn danger" @click="remove(row.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
