# Render 云端部署保姆级教程（Python 后端 · 零基础版）

> 目标：把你电脑上的 Python 网页项目部署到 Render 云平台，得到一个公开网址，
> 评委随时点开就能访问，**你的电脑关不关机都不影响**，全程 0 元。

---

## 整体流程图

```
第 1 步  注册 GitHub 账号          （代码的"网盘"，约 5 分钟）
第 2 步  把项目代码上传到 GitHub    （约 10 分钟）
第 3 步  注册 Render 并授权        （约 3 分钟）
第 4 步  在 Render 创建服务并部署   （约 15 分钟）
第 5 步  注册 Supabase 免费数据库   （约 10 分钟，如果项目用了数据库）
第 6 步  注册 UptimeRobot 保活     （约 5 分钟）
第 7 步  验收测试                 （约 5 分钟）
```

---

## 开始前必须知道的 3 件事

1. **代码里不能写死 `127.0.0.1` 或 `localhost`**。Render 会分配一个动态端口，
   你的程序必须读取环境变量 `PORT` 来监听（第 4.5 节会教你改，只需改一两行）。
2. **`.env` 文件、密码、API 密钥不要上传到 GitHub**。密钥一律填在 Render 的
   环境变量设置里（第 4.4 节）。
3. **Render 免费 Postgres 数据库 30 天就过期**，所以数据库用 Supabase（第 5 步），
   不要用 Render 自带的。

---

## 第 1 步：注册 GitHub 账号

1. 打开浏览器，访问 `https://github.com`
2. 点击右上角 **Sign up**
3. 填写邮箱、密码、用户名（用户名会出现在网址里，建议用拼音或英文）
4. 去邮箱收验证码，输入验证完成注册
5. 登录后你会进入 GitHub 首页

> GitHub 相当于代码的"网盘 + 版本管理"，Render 只能从 GitHub 拉取代码来部署。

---

## 第 2 步：把项目代码上传到 GitHub

### 2.1 创建仓库

1. 登录 GitHub 后，点击右上角 **+** 号 → **New repository**
2. 填写：
   - **Repository name**：项目英文名，比如 `my-competition-app`
   - **可见性**：选 **Private**（私有）也可以，Render 有权限访问
3. 勾选 **Add a README file**（可选）
4. 点击绿色按钮 **Create repository**

### 2.2 上传代码（不会用 Git 命令也能做）

**方式 A：网页直接上传（适合文件不多的情况）**

1. 打开刚创建的仓库页面
2. 点击 **Add file** → **Upload files**
3. 把整个项目的文件**拖拽**进页面（注意：是把文件夹里的内容拖进来，不是文件夹本身）
4. 等待上传完成，点击底部绿色按钮 **Commit changes**

> 注意：网页上传**不能直接传文件夹**。如果项目文件夹层级多，
> 推荐用方式 B。

**方式 B：安装 GitHub Desktop（图形界面，推荐）**

1. 下载安装：`https://desktop.github.com`
2. 打开 GitHub Desktop，登录你的 GitHub 账号
3. 菜单 **File** → **Add local repository** → 选择你的项目文件夹
   （会提示"不是 git 仓库"，点 **Create a repository**，名字随便，点 **Create**）
4. 点击顶部 **Publish repository**（发布仓库），保持 Private 勾选，点 **Publish**
5. 以后每次改完代码，在 GitHub Desktop 里填一句说明 → 点 **Commit to main**
   → 点 **Push origin**，就同步到 GitHub 了

### 2.3 确认项目里有两个关键文件

Render 部署 Python 项目需要：

- **`requirements.txt`** —— 依赖清单。如果还没有，在你项目环境里运行：
  ```
  pip freeze > requirements.txt
  ```
  或者手动列出用到的库，每行一个，例如：
  ```
  flask==3.0.0
  gunicorn==21.2.0
  ```
- **入口文件**（比如 `app.py` 或 `main.py`）—— 记住文件名和里面的应用变量名，
  第 4 步要用。

---

## 第 3 步：注册 Render 并授权 GitHub

1. 打开 `https://render.com`
2. 点击右上角 **Get Started** / **Sign in**
3. 选择 **GitHub** 登录（用第 1 步注册的账号）
4. 授权页面点 **Authorize Render**
5. 进入控制台（Dashboard）

> 全程不需要信用卡，免费额度 750 小时/月，跑满一个月都够。

---

## 第 4 步：创建 Web Service 并部署

### 4.1 新建服务

1. 在 Render 控制台点击右上角 **New +** → 选择 **Web Service**
2. 如果提示连接 GitHub 仓库：点 **Configure account** → 选 **All repositories**
   （或只授权你的项目仓库）→ 保存
3. 在仓库列表中找到你的项目，点击 **Connect**

### 4.2 填写部署配置（重点！）

| 配置项 | 填什么 |
|---|---|
| **Name** | 项目名（会决定网址，如 `my-app` → 网址 `my-app.onrender.com`） |
| **Region** | 选 `Singapore`（离中国最近，访问较快） |
| **Branch** | `main` |
| **Runtime** | 选 **Python 3** |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | 见下方 4.3，取决于你的框架 |
| **Instance Type** | 选 **Free**（默认就是） |

### 4.3 Start Command 怎么写（Python 两种情况）

**如果你的项目是 Flask**（代码里有 `app = Flask(__name__)`）：

```
gunicorn app:app
```

**如果你的项目是 FastAPI**（代码里有 `app = FastAPI()`）：

```
uvicorn app:app --host 0.0.0.0 --port $PORT
```

> 规则：`app:app` 的意思是「入口文件名 : 应用变量名」。
> 如果你的入口文件叫 `main.py`，就写 `gunicorn main:app`。
> 如果 gunicorn 报错找不到应用，检查这两处名字是否对得上。

### 4.4 配置环境变量（数据库密码、API 密钥都填这里）

在创建页面往下拉，找到 **Environment Variables**（或部署后在服务页面的
**Environment** 标签页）：

- 点 **Add Environment Variable**
- 左边填变量名（和你代码里读的名字一致，比如 `DATABASE_URL`）
- 右边填值（比如 Supabase 给你的连接串）
- 有几个密钥就加几条

### 4.5 修改代码：监听 Render 的动态端口（最容易翻车的一步）

Render 会通过环境变量 `PORT` 告诉你的程序该监听哪个端口。
找到你项目入口文件（`app.py`）**最底部**的启动代码，改成这样：

**Flask：**

```python
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # 云平台用分配的端口，本地默认 5000
    app.run(host="0.0.0.0", port=port)
```

**FastAPI + uvicorn：**

```python
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

> 改完后记得用 GitHub Desktop 提交并推送（Commit + Push），
> Render 会自动重新部署。

### 4.6 点击部署

拉到页面底部，点 **Deploy Web Service**。

- 页面会显示实时日志（Logs），第一次部署要 3~10 分钟
- 看到日志出现 `Your service is live 🎉` 之类的字样，并且页面顶部状态变为
  **Live**，就成功了
- 页面顶部会显示你的公网网址：`https://你的项目名.onrender.com`
  **这个网址就是给评委访问的网址！**

> 如果部署失败：点开 **Events** 或 **Logs** 标签，看红色报错行。
> 90% 的失败原因是：requirements.txt 缺依赖、Start Command 写错、
> 代码监听端口没改。修好后 Push 一次就会自动重新部署。

---

## 第 5 步：注册 Supabase 免费数据库（项目用了数据库才需要）

> 如果你的项目没连数据库（数据存在文件里），跳过这一步。

1. 打开 `https://supabase.com` → **Start your project** → 用 GitHub 登录
2. 点 **New project**：
   - Name：随便起
   - Database Password：**设一个强密码并抄在本地记事本上**（只显示一次）
   - Region：选 `Singapore`
3. 创建完成后（约 2 分钟），点顶部 **Connect** 按钮
4. 找到 **Connection string** 里的 URI，形如：
   ```
   postgresql://postgres.abc123:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
   ```
5. 把 `[YOUR-PASSWORD]` 替换成你刚才设置的数据库密码
6. 回到 Render 你的服务 → **Environment** 标签 → 添加环境变量：
   - 变量名：`DATABASE_URL`（必须和你代码里读的一致）
   - 值：粘贴刚才替换好密码的连接串
7. 点 **Save Changes**，Render 会自动重启服务

> 代码里连接数据库的地方，改成从环境变量读取，例如：
> ```python
> import os
> DATABASE_URL = os.environ["DATABASE_URL"]
> ```
> 另外，原数据库里的建表语句（CREATE TABLE...）需要在 Supabase 的
> **SQL Editor** 里执行一遍，并把原有数据导入。

---

## 第 6 步：UptimeRobot 保活（防止休眠）

> Render 免费实例 15 分钟没人访问就休眠，下次访问要等约 1 分钟。
> 用 UptimeRobot 每 10 分钟自动访问一次，让服务一直保持唤醒。

1. 打开 `https://uptimerobot.com` → **Sign Up** 免费注册
2. 登录后点 **+ Add New Monitor**
3. 填写：
   - **Monitor Type**：选 `HTTP(s)`
   - **Friendly Name**：随便，比如 `my-app-keepalive`
   - **URL**：填你的 Render 网址 `https://你的项目名.onrender.com`
   - **Monitoring Interval**：选 `10 minutes`（免费版默认就是）
4. 点 **Create Monitor** 完成

> 提示：也可以再让 Render 服务本身配合——在 Render 服务页 → **Cron Jobs**
> 不需要；UptimeRobot 的 ping 已足够。免费额度 750 小时/月 > 每月总小时数，
> 所以全天保活不会产生费用。

---

## 第 7 步：验收测试（参赛前必做）

1. **自己用手机关掉 Wi-Fi、用流量**打开你的 Render 网址，确认能访问、功能正常
2. **把家里电脑关机**，10 分钟后再用手机访问一次，确认依然正常
   （这就证明评委访问不依赖你的电脑）
3. 把网址发给一位同学，用他的设备也测一遍
4. 测试所有核心功能：登录、提交、查询、文件上传等
5. **比赛前一晚**再完整测一遍；演示当天提前 1 分钟自己先点开一次"预热"

---

## 常见问题排查

| 现象 | 原因与解决 |
|---|---|
| 部署一直失败（Deploy failed） | 看 Logs 红色行：多半是 requirements.txt 缺包或 Start Command 写错 |
| 打开网址显示 `Application error` | 代码崩了，看 Logs；检查环境变量名和代码里读的是否一致 |
| 第一次打开要等 30~60 秒 | 免费实例冷启动，正常现象；UptimeRobot 保活后基本不会再遇到 |
| 数据库连接报错 | 检查 Supabase 连接串里的密码是否替换、环境变量是否保存 |
| 免费实例内存不足（512MB） | 别在云上跑重型计算/大模型，演示版尽量轻量 |
| 改了代码网址没变化 | 代码要 Commit + Push 到 GitHub 才会触发自动重新部署 |

---

## 费用与时间线确认

- Render 免费 Web Service：**0 元，不限 3 个月**
- Supabase 免费数据库：**0 元，长期有效**（注意：90 天不活跃的项目会被暂停，
  保活期间 UptimeRobot 的访问 + 你们的正常使用足以保持活跃）
- UptimeRobot 免费版：**0 元**
- 总花费：**0 元** ✅
