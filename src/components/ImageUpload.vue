<template>
  <div class="upload-component">
    <el-upload
      class="upload-dragger"
      drag
      action="#"
      :auto-upload="false"
      :on-change="handleChange"
      :show-file-list="false"
      accept=".jpg,.jpeg,.png"
    >
      <div v-if="imageUrl" class="preview-container">
        <img :src="imageUrl" class="preview-image" />
        <div class="re-upload-mask">
          <el-icon class="re-upload-icon"><UploadFilled /></el-icon>
          <span>点击或拖拽更换图片</span>
        </div>
      </div>
      <div v-else class="upload-placeholder">
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处 或 <em>点击上传</em>
        </div>
        <div class="el-upload__tip">
          支持 JPG/PNG 格式，大小不超过 10MB
        </div>
      </div>
    </el-upload>

    <div v-if="uploading" class="progress-bar">
      <el-progress :percentage="progress" :status="progressStatus" />
      <p class="upload-text">正在上传处理中...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, type UploadFile } from 'element-plus'

const emit = defineEmits(['upload-success'])

const imageUrl = ref('')
const uploading = ref(false)
const progress = ref(0)
const progressStatus = ref('')

const handleChange = (uploadFile: UploadFile) => {
  const rawFile = uploadFile.raw
  if (!rawFile) return

  // Validate format
  const isJPG = rawFile.type === 'image/jpeg' || rawFile.type === 'image/png'
  if (!isJPG) {
    ElMessage.error('上传图片只能是 JPG 或 PNG 格式!')
    return
  }

  // Validate size (10MB)
  const isLt10M = rawFile.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('上传图片大小不能超过 10MB!')
    return
  }

  // Preview
  imageUrl.value = URL.createObjectURL(rawFile)
  
  // Simulate upload process
  startUpload(rawFile)
}

const startUpload = (file: File) => {
  uploading.value = true
  progress.value = 0
  progressStatus.value = ''

  // Simulate progress
  const timer = setInterval(() => {
    progress.value += 10
    if (progress.value >= 100) {
      clearInterval(timer)
      uploading.value = false
      progressStatus.value = 'success'
      progressStatus.value = 'success'
      // ElMessage.success('上传成功') // 移除了这里误导性的成功提示，由父组件负责后续反馈
      emit('upload-success', { file, url: imageUrl.value })
    }
  }, 200)
}
</script>

<style scoped>
.upload-component {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.upload-dragger :deep(.el-upload-dragger) {
  width: 100%;
  height: 300px; /* Reduced height */
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f9fafb;
  border: 2px dashed #d1d5db; /* Lighter border */
  border-radius: 16px;
  transition: all 0.3s;
}

.upload-dragger :deep(.el-upload-dragger:hover),
.upload-dragger :deep(.el-upload-dragger.is-dragover) {
  border-color: #10b981;
  background-color: #ecfdf5;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #9ca3af;
}

.el-icon--upload {
  font-size: 60px;
  margin-bottom: 16px;
  color: #d1d5db;
}

.el-upload__text {
  font-size: 16px;
  color: #374151;
  margin-bottom: 8px;
}

.el-upload__text em {
  color: #10b981;
  font-style: normal;
  font-weight: bold;
}

.el-upload__tip {
  color: #9ca3af;
  font-size: 12px;
}

.preview-container {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  border-radius: 14px;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.re-upload-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  opacity: 0;
  transition: opacity 0.3s;
  color: #fff;
}

.preview-container:hover .re-upload-mask {
  opacity: 1;
}

.re-upload-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.progress-bar {
  margin-top: 20px;
}

.upload-text {
  text-align: center;
  margin-top: 8px;
  color: #6b7280;
  font-size: 14px;
}
</style>
