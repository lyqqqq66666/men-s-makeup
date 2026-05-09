<template>
  <div class="upload-view-container">
    <ModernBackground :enableLines="false" />
    <div 
      class="content-box" 
      @mouseenter="isHovering = true" 
      @mouseleave="isHovering = false"
    >
      <div class="back-btn-wrapper">
        <el-button link :icon="ArrowLeft" @click="router.back()" class="custom-back-btn">
          返回上一页
        </el-button>
      </div>

      <h2 class="page-title">上传人像照片</h2>
      <p class="page-subtitle">请上传一张清晰的正面人像照片，我们将为您进行智能矫正与美妆</p>
      
      <div class="upload-area">
        <ImageUpload @upload-success="handleUploadSuccess" />
      </div>

      <div class="tips-area">
        <h3><el-icon><InfoFilled /></el-icon> 温馨提示</h3>
        <ul>
          <li>建议上传光线充足、五官清晰的正面照片</li>
          <li>支持 JPG/PNG 格式，文件大小不超过 10MB</li>
          <li>上传后系统将自动进行人脸检测</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ImageUpload from '../components/ImageUpload.vue'
import ModernBackground from '../components/ModernBackground.vue'
import { InfoFilled, ArrowLeft } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElLoading } from 'element-plus'
import { createMakeupSessionApi } from '@/api/makeup'

const router = useRouter()
const isHovering = ref(false)

const handleUploadSuccess = async (data: { file: File, url: string }) => {
  const loading = ElLoading.service({
    lock: true,
    text: '正在创建试妆会话...',
    background: 'rgba(0, 0, 0, 0.7)',
  })

  try {
    console.log('>>> [Debug] UploadView handleUploadSuccess. File:', data.file.name)

    // 仅创建试妆 Session，跳过分析流程，直接进入化妆页
    const formData = new FormData()
    formData.append('image', data.file)

    console.log('>>> [Debug] 准备调用 createMakeupSessionApi...')
    const sessionRes = await createMakeupSessionApi(formData, true) as any
    console.log('>>> [Debug] createMakeupSessionApi 响应:', sessionRes)

    const sessionId =
      sessionRes?.data?.session_id ||
      sessionRes?.session_id ||
      ''
    const code = sessionRes?.code
    const isCodeSuccess = code === 0 || code === 200 || code === undefined || code === null

    if (!isCodeSuccess || !sessionId) {
      throw new Error(sessionRes.message || '试妆会话创建失败')
    }

    ElMessage.success('上传成功，已进入化妆页')
    router.push({
      name: 'Result',
      query: {
        img: data.url,
        season: '温润秋季型',
        session_id: sessionId
      }
    })
  } catch (error: any) {
    console.error('>>> [Debug] Upload processing error:', error)
    ElMessage.error(error.message || '上传失败，请重试')
  } finally {
    loading.close()
  }
}
</script>

<style scoped>
.upload-view-container {
  min-height: 100vh;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: #1f2937;
  overflow: hidden;
}

.content-box {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 600px; /* Reduced width */
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 40px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.05);
  border: 1px solid rgba(0, 0, 0, 0.05);
  animation: fadeIn 0.8s ease-out;
}

.back-btn-wrapper {
  position: absolute;
  top: 24px;
  left: 24px;
}

.custom-back-btn {
  font-size: 14px;
  color: #6b7280;
  transition: all 0.3s ease;
}

.custom-back-btn:hover {
  color: #10b981;
  transform: translateX(-2px);
}

.page-title {
  text-align: center;
  font-size: 28px;
  margin-bottom: 12px;
  font-weight: 600;
  background: linear-gradient(to right, #10b981, #059669);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.page-subtitle {
  text-align: center;
  color: #6b7280;
  margin-bottom: 30px;
  font-size: 14px;
}

.upload-area {
  margin-bottom: 30px;
}

.tips-area {
  background: #f9fafb;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}

.tips-area h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  margin-bottom: 12px;
  color: #10b981;
}

.tips-area ul {
  list-style: none;
  padding-left: 20px;
  margin: 0;
}

.tips-area li {
  position: relative;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.8;
  margin-bottom: 6px;
}

.tips-area li::before {
  content: "";
  position: absolute;
  left: -15px;
  top: 7px;
  width: 5px;
  height: 5px;
  background-color: #10b981;
  border-radius: 50%;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
