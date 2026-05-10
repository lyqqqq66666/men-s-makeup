<template>
  <div class="camera-capture-component">
    <!-- 摄像头预览模式 -->
    <div v-if="!capturedPhoto && state.isCameraOpen" class="camera-container">
      <video ref="videoRef" class="video-preview" autoplay playsinline muted></video>

      <div v-if="guideVisible" class="face-guide">
        <div class="guide-oval"></div>
        <p class="guide-text">请将面部对准框内</p>
      </div>

      <!-- 倒计时显示 -->
      <div v-if="countdown > 0" class="countdown-overlay">
        <div class="countdown-number">{{ countdown }}</div>
        <p class="countdown-text">即将自动拍照</p>
      </div>

      <div class="capture-controls">
        <button class="control-btn switch-btn" @click="switchCamera" title="切换摄像头">
          <el-icon><RefreshRight /></el-icon>
        </button>
        <button class="control-btn capture-btn" @click="manualCapture" :disabled="countdown > 0">
          <div class="capture-ring"></div>
        </button>
        <button class="control-btn close-btn" @click="closeCamera" title="关闭摄像头">
          <el-icon><Close /></el-icon>
        </button>
      </div>

      <canvas ref="canvasRef" style="display: none"></canvas>
    </div>

    <!-- 拍照预览模式 -->
    <div v-if="capturedPhoto && !state.isCameraOpen" class="preview-container">
      <div class="preview-header">
        <h3>预览照片</h3>
      </div>
      <div class="preview-image-wrapper">
        <img :src="capturedPhoto" alt="拍摄的照片" class="preview-image" />
      </div>
      <div class="preview-controls">
        <el-button type="primary" size="large" @click="confirmPhoto" class="confirm-btn">
          <el-icon><Check /></el-icon>
          确认使用
        </el-button>
        <el-button size="large" @click="retake" class="retake-btn">
          <el-icon><RefreshLeft /></el-icon>
          重新拍摄
        </el-button>
      </div>
    </div>

    <!-- 未开启摄像头 -->
    <div v-if="!state.isCameraOpen && !capturedPhoto" class="camera-placeholder" @click="openCamera">
      <div class="placeholder-icon">
        <el-icon><Camera /></el-icon>
      </div>
      <div class="placeholder-text">点击开启摄像头</div>
      <div class="placeholder-hint">拍照上传人像照片</div>
    </div>

    <div v-if="state.errorMessage" class="error-tip">
      <el-icon><WarningFilled /></el-icon>
      <span>{{ state.errorMessage }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted, nextTick } from 'vue'
import { Camera, RefreshRight, Close, WarningFilled, Check, RefreshLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

interface Props {
  facingMode?: 'user' | 'environment'
  guideVisible?: boolean
  autoCaptureDelay?: number
}

const props = withDefaults(defineProps<Props>(), {
  facingMode: 'user',
  guideVisible: true,
  autoCaptureDelay: 3
})

interface CaptureData {
  file: File
  url: string
}

const emit = defineEmits<{
  (e: 'capture-success', data: CaptureData): void
  (e: 'capture-cancel'): void
  (e: 'error', message: string): void
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)

const state = reactive({
  isCameraOpen: false,
  stream: null as MediaStream | null,
  facingMode: props.facingMode as 'user' | 'environment',
  errorMessage: ''
})

const capturedPhoto = ref<string>('')
const countdown = ref(0)
let countdownTimer: number | null = null

const checkCameraSupport = (): boolean => {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
}

const isSecureContext = (): boolean => {
  return window.isSecureContext
}

const openCamera = async () => {
  if (!checkCameraSupport()) {
    state.errorMessage = '您的浏览器不支持摄像头功能，请使用本地上传'
    emit('error', state.errorMessage)
    ElMessage.warning('您的浏览器不支持摄像头功能')
    return
  }

  if (!isSecureContext()) {
    state.errorMessage = '摄像头需要在安全环境（HTTPS或localhost）下使用'
    emit('error', state.errorMessage)
    ElMessage.warning('请在 HTTPS 或 localhost 环境下使用摄像头')
    return
  }

  try {
    const constraints: MediaStreamConstraints = {
      video: {
        facingMode: state.facingMode,
        width: { ideal: 1280 },
        height: { ideal: 720 }
      }
    }

    state.stream = await navigator.mediaDevices.getUserMedia(constraints)
    state.isCameraOpen = true
    state.errorMessage = ''
    capturedPhoto.value = ''

    await nextTick()
    if (videoRef.value) {
      videoRef.value.srcObject = state.stream
      videoRef.value.play().catch(err => {
        console.warn('Auto-play blocked, video may not display:', err)
      })
    }

    startCountdown()
  } catch (err: any) {
    console.error('Camera access error:', err)
    if (err.name === 'NotAllowedError') {
      state.errorMessage = '摄像头权限被拒绝，请在浏览器设置中允许访问摄像头'
      ElMessage.error('摄像头权限被拒绝，请在浏览器设置中允许访问摄像头')
    } else if (err.name === 'NotFoundError') {
      state.errorMessage = '未找到摄像头设备，请确认设备已正确连接'
      ElMessage.error('未找到摄像头设备')
    } else {
      state.errorMessage = '无法访问摄像头，请检查设备连接或浏览器权限设置'
      emit('error', state.errorMessage)
    }
    state.isCameraOpen = false
  }
}

const startCountdown = () => {
  countdown.value = props.autoCaptureDelay

  countdownTimer = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(countdownTimer!)
      countdownTimer = null
      autoCapture()
    }
  }, 1000)
}

const autoCapture = () => {
  capturePhoto()
}

const manualCapture = () => {
  if (countdown.value > 0) {
    clearInterval(countdownTimer!)
    countdownTimer = null
    countdown.value = 0
  }
  capturePhoto()
}

const capturePhoto = () => {
  const video = videoRef.value
  const canvas = canvasRef.value

  if (!video || !canvas) {
    ElMessage.error('拍照失败，请重试')
    return
  }

  if (video.videoWidth === 0 || video.videoHeight === 0) {
    ElMessage.error('视频流未就绪，请稍后重试')
    return
  }

  canvas.width = video.videoWidth
  canvas.height = video.videoHeight

  const ctx = canvas.getContext('2d')
  if (!ctx) {
    ElMessage.error('无法创建画布上下文')
    return
  }

  ctx.drawImage(video, 0, 0)

  canvas.toBlob(
    (blob) => {
      if (!blob) {
        ElMessage.error('图片生成失败，请重试')
        return
      }

      const url = URL.createObjectURL(blob)
      capturedPhoto.value = url
      closeCamera()
    },
    'image/jpeg',
    0.92
  )
}

const confirmPhoto = () => {
  const canvas = canvasRef.value
  if (!canvas || !capturedPhoto.value) {
    ElMessage.error('照片数据无效，请重新拍摄')
    return
  }

  fetch(capturedPhoto.value)
    .then(res => res.blob())
    .then(blob => {
      const file = new File([blob], `camera_${Date.now()}.jpg`, {
        type: 'image/jpeg',
        lastModified: Date.now()
      })

      emit('capture-success', { file, url: capturedPhoto.value })
    })
    .catch(() => {
      ElMessage.error('图片处理失败，请重新拍摄')
    })
}

const retake = () => {
  if (capturedPhoto.value) {
    URL.revokeObjectURL(capturedPhoto.value)
    capturedPhoto.value = ''
  }
  openCamera()
}

const switchCamera = async () => {
  closeCamera()
  state.facingMode = state.facingMode === 'user' ? 'environment' : 'user'
  await openCamera()
}

const closeCamera = () => {
  if (state.stream) {
    state.stream.getTracks().forEach((track) => track.stop())
    state.stream = null
  }
  state.isCameraOpen = false

  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  countdown.value = 0

  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
}

onUnmounted(() => {
  closeCamera()
  if (capturedPhoto.value) {
    URL.revokeObjectURL(capturedPhoto.value)
  }
})
</script>

<style scoped>
.camera-capture-component {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.camera-placeholder {
  width: 100%;
  height: 300px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background-color: #f9fafb;
  border: 2px dashed #10b981;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.camera-placeholder:hover {
  background-color: #ecfdf5;
  border-color: #059669;
}

.placeholder-icon {
  font-size: 60px;
  color: #10b981;
  margin-bottom: 16px;
}

.placeholder-text {
  font-size: 18px;
  color: #374151;
  font-weight: 500;
  margin-bottom: 8px;
}

.placeholder-hint {
  font-size: 14px;
  color: #9ca3af;
}

.camera-container {
  position: relative;
  width: 100%;
  height: 300px;
  border-radius: 16px;
  overflow: hidden;
  background-color: #000;
}

.video-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.face-guide {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.guide-oval {
  width: 200px;
  height: 260px;
  border: 3px dashed rgba(16, 185, 129, 0.7);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.guide-text {
  text-align: center;
  color: rgba(255, 255, 255, 0.9);
  margin-top: 12px;
  font-size: 14px;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}

@keyframes pulse {
  0%,
  100% {
    border-color: rgba(16, 185, 129, 0.3);
  }
  50% {
    border-color: rgba(16, 185, 129, 0.9);
  }
}

.countdown-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 10;
}

.countdown-number {
  font-size: 80px;
  font-weight: bold;
  color: #fff;
  text-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  animation: countdownPulse 1s ease-in-out infinite;
}

.countdown-text {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.9);
  margin-top: 8px;
}

@keyframes countdownPulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
}

.capture-controls {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 32px;
}

.control-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background-color: rgba(255, 255, 255, 0.9);
  color: #374151;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 20px;
}

.control-btn:hover:not(:disabled) {
  background-color: #fff;
  transform: scale(1.05);
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.switch-btn {
  background-color: rgba(0, 0, 0, 0.5);
  color: #fff;
}

.switch-btn:hover:not(:disabled) {
  background-color: rgba(0, 0, 0, 0.7);
}

.close-btn {
  background-color: rgba(239, 68, 68, 0.8);
  color: #fff;
}

.close-btn:hover:not(:disabled) {
  background-color: rgba(239, 68, 68, 1);
}

.capture-btn {
  width: 72px;
  height: 72px;
  border: 4px solid #fff;
  background-color: transparent;
  position: relative;
}

.capture-ring {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background-color: #fff;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  transition: all 0.15s;
}

.capture-btn:hover:not(:disabled) .capture-ring {
  transform: translate(-50%, -50%) scale(1.05);
  background-color: #10b981;
}

.capture-btn:active:not(:disabled) .capture-ring {
  transform: translate(-50%, -50%) scale(0.9);
  background-color: #10b981;
}

/* 预览模式 */
.preview-container {
  width: 100%;
  height: 300px;
  display: flex;
  flex-direction: column;
  background-color: #f9fafb;
  border: 2px solid #e5e7eb;
  border-radius: 16px;
  overflow: hidden;
}

.preview-header {
  padding: 12px 16px;
  background-color: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.preview-header h3 {
  margin: 0;
  font-size: 16px;
  color: #374151;
  font-weight: 500;
}

.preview-image-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px;
  min-height: 0;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 8px;
}

.preview-controls {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background-color: #fff;
  border-top: 1px solid #e5e7eb;
}

.confirm-btn,
.retake-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.confirm-btn {
  background-color: #10b981 !important;
  border-color: #10b981 !important;
  color: #fff !important;
}

.confirm-btn:hover {
  background-color: #059669 !important;
  border-color: #059669 !important;
}

.retake-btn {
  background-color: #fff !important;
  border-color: #d1d5db !important;
  color: #374151 !important;
}

.retake-btn:hover {
  background-color: #f9fafb !important;
  border-color: #10b981 !important;
  color: #10b981 !important;
}

.error-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
  padding: 12px 16px;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 14px;
}

.error-tip .el-icon {
  font-size: 18px;
}
</style>
