# ShadeCanopy-01 · 分区气候日志与轮灌计划

温室「分区气候日志与轮灌计划」全栈种子项目（非考勤 OA、非库存）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python Django 5 · Django REST Framework · SimpleJWT · django-cors-headers · Gunicorn |
| 前端 | Vue 3 · Vite · Pinia · Vue Router |
| 数据库 | PostgreSQL 15 |
| 部署 | Docker Compose · Nginx（前端容器反代 `/api` → Django） |

## 路径与端口

- **项目路径**：`D:\work\document\bytecode\claudeCodePro\ShadeCanopy\ShadeCanopy-01\`
- **前端**：http://localhost:3500
- **后端 API**：http://localhost:8500（也可经前端同源 `/api` 访问）
- **PostgreSQL**：localhost:5435

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | admin（管理员，可进 Django Admin） |
| `grower` | `123456` | grower（种植员） |

启动时 `entrypoint.sh` 会执行 `migrate` + `seed_data` 自动写入账号与示例业务数据。
种子数据中分区 `A-01` 设有**今日（东八区）湿度上限 60%**，并预置一条湿度 78.5% 的气候记录
（会撞上限的示例）：在气候日志页新建/更新 `A-01` 当日湿度 > 60% 的记录会被 400 拒绝并提示上限账编号。

## 快速启动

```bash
cd D:\work\document\bytecode\claudeCodePro\ShadeCanopy\ShadeCanopy-01
docker compose up --build
```

浏览器打开 http://localhost:3500 ，使用 `grower` / `123456` 登录。

停止：

```bash
docker compose down
```

## 业务模块

1. **Auth**：JWT `POST /api/auth/token/`，当前用户 `GET /api/auth/me/`
2. **Greenhouse**：name / location / areaM2 / notes
3. **Zone**：greenhouseId / zoneCode / cropName / status(`idle|growing|fallow`)；同温室 zoneCode 唯一；每行带 `todayCapPct`（今日湿度上限，无则空）
4. **ClimateLog**：zoneId / recordedAt / tempC / humidityPct / parUmol / co2Ppm；**humidityPct ∈ [20, 100]**；写入时按东八区自然日校验湿度上限（见下节）
5. **HumidityCap（湿度上限账）**：zoneId / workDate / capPct / setBy；同区同日唯一；capPct 为 40～100 的整数
6. **IrrigationCycle**：zoneId / startAt / durationMin / waterLiters / status(`scheduled|running|done|skipped`)
7. **Dashboard**：温室数、growing 分区数、近 24h 气候日志数、今日 scheduled 轮灌数、已设上限区数（今日设有上限账的分区数，与分区列表「今日湿度上限」非空行数一致）→ `GET /api/dashboard/`

## 湿度上限与东八区归日规则

- **上限账字段**：所属分区（zoneId）、作业日（workDate）、湿度上限（capPct，40～100 的整数）、设定人（setBy，保存时自动记为当前登录用户）。**同一分区同一作业日唯一**。
- **归日规则**：一律按**东八区（UTC+8，固定偏移）自然日**归日，与服务器本地时区、浏览器时区均无关。
  即把采样时刻 `recordedAt` 换算到 UTC+8 后取日期作为作业日。例如：
  - `2026-09-21T23:30:00+08:00` → 作业日 `2026-09-21`
  - `2026-09-21T16:30:00Z`（= 东八区次日 00:30）→ 作业日 `2026-09-22`
- **拦截规则**：新建气候记录、以及单条更新气候记录（PUT/PATCH）走同一套判定——
  按 `recordedAt` 的东八区日期找到该分区当日的上限账，**湿度严格大于上限**即返回 `400`，
  中文报错中带上限账编号（如 `上限账 #1（作业日 2026-09-21，湿度上限 60%）`）；
  当日没有上限账则不拦截。
- **展示**：分区列表每行带「今日湿度上限」（当天上限或空）；仪表盘「已设上限区数」
  统计今日设有上限账的分区数，与列表非空今日上限行数一致。
- **维护入口**：分区管理页的「湿度上限账」面板可按分区维护各作业日上限（同区同日重复保存会覆盖更新）。

## API 一览

| 方法 | 路径 |
| --- | --- |
| POST | `/api/auth/token/` |
| POST | `/api/auth/token/refresh/` |
| GET | `/api/auth/me/` |
| CRUD | `/api/greenhouses/` |
| CRUD | `/api/zones/?greenhouseId=&status=` |
| CRUD | `/api/climate-logs/?zoneId=` |
| CRUD | `/api/humidity-caps/?zoneId=&workDate=` |
| CRUD | `/api/irrigation-cycles/?zoneId=&status=` |
| GET | `/api/dashboard/` |

字段对外使用 camelCase（如 `areaM2`、`zoneCode`、`humidityPct`）。

## 本地开发（可选）

**后端**（需本机 Postgres 或已启动 compose 中的 db）：

```bash
cd backend
pip install -r requirements.txt
set POSTGRES_HOST=127.0.0.1
set POSTGRES_PORT=5435
python manage.py migrate
python manage.py seed_data
python manage.py runserver 0.0.0.0:8500
```

**前端**：

```bash
cd frontend
npm install
npm run dev
```

Vite 已将 `/api` 代理到 `http://127.0.0.1:8500`。

## 目录结构

```
ShadeCanopy-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh      # migrate + seed + gunicorn
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/            # settings / urls
│   ├── accounts/          # 自定义 User + role
│   └── core/              # 温室/分区/气候/轮灌 + seed_data
└── frontend/
    ├── Dockerfile
    ├── nginx.conf         # 静态资源 + /api 反代
    ├── package.json
    └── src/               # Vue 页面（叶绿/土色主题）
```

## 配色说明

前端采用叶绿（`#3d6b3a`）与土色（`#8b6b45`）主色，米色底与侧栏深绿渐变，贴近温室场景。
