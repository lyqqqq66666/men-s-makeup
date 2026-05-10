# 摄像头拍照功能实现方案

> 为颜选MenX上传页面新增摄像头实时拍照功能
> 日期: 2026-05-09

---

## 1. 功能概述

在现有上传页面（UploadView.vue）中，新增"拍照上传"入口，用户可以通过摄像头实时拍照来获取人像照片，替代手动上传文件。

### 用户流程

```
上传页面
  ├── 📁 本地上传（现有功能）
  └── 📷 拍照上传（新增功能）
        │
        ▼
    请求摄像头权限
        │
        ├── ✅ 授权成功 → 打开摄像头预览
        │     │
        │     ├── 实时预览画面
        │     ├── 人脸检测引导框（辅助对齐）
        │     ├── 📸 拍照按钮
        │     ├── 🔄 切换前后摄像头
        │     └── ❌ 关闭摄像头
        │
        └── ❌ 授权失败 → 提示用户手动上传
```

---

## 2. 技术方案

### 2.1 核心技术

| 技术 | 用途 | 说明 |
|------|------|------|
| `navigator.mediaDevices.getUserMedia()` | 调用摄像头 | 浏览器原生 API |
| `<video>` 元素 | 实时预览 | 显示摄像头画面 |
| `<canvas>` 元素 | 截图 | 从 video 帧捕获图片 |
| `MediaStream` | 流控制 | 开启/关闭摄像头 |

### 2.2 组件设计

#### 新建组件: `CameraCapture.vue`

```
src/components/CameraCapture.vue
```

**组件职责**：
- 请求摄像头权限
- 显示实时预览画面
- 绘制人脸检测引导框
- 拍照并输出 File 对象
- 支持切换前后摄像头（移动端）

**组件接口**：

```typescript
// Props
interface Props {
  facingMode?: 'user' | 'environment'  // 默认 'user'（前置）
  guideVisible?: boolean                // 是否显示引导框，默认 true
}

// Emits
interface Emits {
  (e: 'capture-success', data: { file: File, url: string }): void
  (e: 'capture-cancel'): void
  (e: 'error', message: string): void
}
```

**组件状态**：

```typescript
const state = reactive({
  isCameraOpen: false,      // 摄像头是否开启
  isCapturing: false,       // 是否正在拍照
  stream: null as MediaStream | null,  // 媒体流
  facingMode: 'user',       // 前/后置
  hasPermission: false,     // 权限状态
  errorMessage: '',         // 错误信息
})
```

### 2.3 修改现有组件

#### 修改: `UploadView.vue`

在页面上传区域新增"拍照上传"按钮，点击后切换到 CameraCapture 组件：

```vue
<template>
  <div class="upload-area">
    <!-- 现有上传组件 -->
    <ImageUpload v-if="!showCamera" @upload-success="handleUploadSuccess" />
    
    <!-- 新增拍照组件 -->
    <CameraCapture 
      v-else 
      @capture-success="handleUploadSuccess"
      @capture-cancel="showCamera = false"
    />
  </div>

  <!-- 切换按钮 -->
  <div class="switch-mode">
    <el-button v-if="!showCamera" @click="showCamera = true">
      <el-icon><Camera /></el-icon> 拍照上传
    </el-button>
    <el-button v-else @click="showCamera = false">
      <el-icon><Upload /></el-icon> 本地上传
    </el-button>
  </div>
</template>
```

---

## 3. 实现细节

### 3.1 CameraCapture.vue 核心逻辑

```typescript
// 1. 开启摄像头
async function openCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: state.facingMode,
        width: { ideal: 1280 },
        height: { ideal: 720 }
      }
    })
    state.stream = stream
    state.isCameraOpen = true
    state.hasPermission = true
    
    // 绑定到 video 元素
    const video = videoRef.value
    if (video) {
      video.srcObject = stream
      await video.play()
    }
  } catch (err) {
    state.errorMessage = '无法访问摄像头，请检查权限设置'
    emit('error', state.errorMessage)
  }
}

// 2. 拍照
function capturePhoto() {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas) return

  // 设置 canvas 尺寸与视频一致
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight

  // 绘制当前帧
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0)

  // 转换为 Blob → File
  canvas.toBlob((blob) => {
    if (!blob) return
    const file = new File([blob], `camera_${Date.now()}.jpg`, {
      type: 'image/jpeg',
      lastModified: Date.now()
    })
    const url = URL.createObjectURL(blob)
    emit('capture-success', { file, url })
    closeCamera()
  }, 'image/jpeg', 0.92)  // JPEG 质量 92%
}

// 3. 关闭摄像头
function closeCamera() {
  if (state.stream) {
    state.stream.getTracks().forEach(track => track.stop())
    state.stream = null
  }
  state.isCameraOpen = false
}

// 4. 切换前后摄像头（移动端）
async function switchCamera() {
  closeCamera()
  state.facingMode = state.facingMode === 'user' ? 'environment' : 'user'
  await openCamera()
}
```

### 3.2 人脸引导框

在摄像头预览上叠加一个半透明引导框，帮助用户对齐面部：

```vue
<template>
  <div class="camera-container">
    <video ref="videoRef" autoplay playsinline />
    
    <!-- 人脸引导框 -->
    <div v-if="guideVisible" class="face-guide">
      <div class="guide-oval"></div>
      <p class="guide-text">请将面部对准框内</p>
    </div>
    
    <!-- 拍照按钮 -->
    <div class="capture-controls">
      <button class="capture-btn" @click="capturePhoto">
        <div class="capture-ring"></div>
      </button>
      <button class="switch-btn" @click="switchCamera">🔄</button>
      <button class="close-btn" @click="closeCamera">✕</button>
    </div>
    
    <canvas ref="canvasRef" style="display: none" />
  </div>
</template>
```

```css
.face-guide {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.guide-oval {
  width: 240px;
  height: 320px;
  border: 3px dashed rgba(16, 185, 129, 0.6);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.guide-text {
  text-align: center;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 12px;
  font-size: 14px;
}

@keyframes pulse {
  0%, 100% { border-color: rgba(16, 185, 129, 0.3); }
  50% { border-color: rgba(16, 185, 129, 0.8); }
}
```

### 3.3 拍照按钮样式

```css
.capture-btn {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  border: 4px solid white;
  background: transparent;
  cursor: pointer;
  position: relative;
}

.capture-ring {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: white;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  transition: transform 0.15s;
}

.capture-btn:active .capture-ring {
  transform: translate(-50%, -50%) scale(0.9);
}
```

---

## 4. 需要修改的文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/components/CameraCapture.vue` | **新建** | 摄像头拍照组件 |
| `src/views/UploadView.vue` | **修改** | 添加拍照入口和切换逻辑 |
| `src/components/ImageUpload.vue` | **不变** | 保持现有功能 |

---

## 5. 兼容性处理

### 5.1 浏览器支持

```typescript
// 检测浏览器是否支持摄像头
function checkCameraSupport(): boolean {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
}

// 不支持时隐藏拍照按钮
const supportsCamera = checkCameraSupport()
```

### 5.2 HTTPS 要求

> `getUserMedia()` 要求在 **HTTPS** 或 **localhost** 环境下使用。

```typescript
// 检测是否安全上下文
function isSecureContext(): boolean {
  return window.isSecureContext
}
```

### 5.3 移动端适配

```typescript
// 移动端默认使用后置摄像头
const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
const defaultFacingMode = isMobile ? 'environment' : 'user'
```

---

## 6. 完整的 CameraCapture.vue 模板结构

```
CameraCapture.vue
├── <div class="camera-container">
│   ├── <video ref="videoRef" />           # 摄像头预览
│   ├── <div class="face-guide">            # 人脸引导框
│   │   ├── <div class="guide-oval" />     # 椭圆引导
│   │   └── <p class="guide-text" />       # 提示文字
│   ├── <div class="capture-controls">      # 控制按钮
│   │   ├── 拍照按钮 (大圆)
│   │   ├── 切换摄像头 (🔄)
│   │   └── 关闭 (✕)
│   └── <canvas ref="canvasRef" hidden />  # 隐藏的截图画布
│
├── <div v-if="!isCameraOpen" class="camera-placeholder">
│   └── 点击开启摄像头
│
└── <div v-if="errorMessage" class="error-tip">
    └── 错误提示信息
```

---

## 7. 给 Code 模式的 Prompt

将以下内容复制到新的 Code with SOLO 会话中：

```
请为我的项目实现摄像头拍照上传功能。

项目路径: /sessions/69feabc952bcaf2d1c9864fd/workspace/MenX/智颜方正—智能图像矫正与风格男妆生成系统/

需要做的事情：

1. 新建 src/components/CameraCapture.vue 组件
   - 使用 navigator.mediaDevices.getUserMedia() 调用摄像头
   - 显示实时预览画面
   - 添加人脸引导框（椭圆形虚线框 + "请将面部对准框内" 提示）
   - 拍照按钮（大圆形白色按钮，仿手机相机风格）
   - 支持切换前后摄像头（移动端）
   - 拍照后通过 canvas 截图，转换为 File 对象
   - emit('capture-success', { file: File, url: string }) 事件
   - emit('capture-cancel') 事件
   - 关闭时释放摄像头资源

2. 修改 src/views/UploadView.vue
   - 在上传区域下方添加"📷 拍照上传"按钮
   - 点击后显示 CameraCapture 组件，隐藏 ImageUpload
   - 添加"📁 本地上传"按钮切换回来
   - CameraCapture 的 capture-success 事件复用现有的 handleUploadSuccess 方法
   - 不支持摄像头的浏览器隐藏拍照按钮

技术要求：
- Vue 3 Composition API (<script setup>)
- TypeScript
- Tailwind CSS + 现有样式风格（主色 #10b981 绿色）
- Element Plus 图标
- 不需要安装额外依赖

请先读取现有的 UploadView.vue 和 ImageUpload.vue 了解代码风格，然后实现功能。
```

---

## 8. 验收标准

- [ ] 点击"拍照上传"按钮可以打开摄像头
- [ ] 实时预览画面流畅
- [ ] 人脸引导框正确显示
- [ ] 点击拍照按钮可以截取图片
- [ ] 截取的图片能正确传递到后续试妆流程
- [ ] 可以切换回本地上传模式
- [ ] 关闭摄像头时正确释放资源
- [ ] 不支持摄像头的浏览器不显示拍照按钮
