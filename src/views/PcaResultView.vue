<template>
  <div class="pca-container">
    <ModernBackground />
    
    <div class="content-wrapper">
      <div class="glass-panel">
        <h2 class="title">智颜解析档案</h2>
        <p class="subtitle">基于百万级面部色彩数据，为您生成专属美学报告</p>

        <div class="report-content">
          <!-- Left: User Avatar -->
          <div class="avatar-section">
            <div class="avatar-frame">
              <img :src="uploadedImage" alt="用户照片" v-if="uploadedImage" />
              <div v-else class="placeholder-avatar">
                <el-icon><UserFilled /></el-icon>
              </div>
            </div>
            <div class="avatar-badge">矫正完成</div>
          </div>

          <!-- Right: PCA Results -->
          <div class="result-section">
            <div class="season-badge">
              <span class="label">专属季型</span>
              <span class="value">{{ mockResult.season }}</span>
            </div>
            <p class="season-desc">{{ mockResult.description }}</p>

            <div class="color-palette-group">
              <div class="palette-block">
                <h3><el-icon><Check /></el-icon> 推荐专属色 (PANTONE® 分子式)</h3>
                <div class="color-list pantone-list">
                  <div class="pantone-card" v-for="(color, index) in mockResult.recommendedColors" :key="index">
                    <div class="pantone-color-area" :style="{ backgroundColor: color.hex }"></div>
                    <div class="pantone-info-area">
                      <div class="pantone-title">PANTONE®</div>
                      <div class="pantone-code">{{ color.pantone }}</div>
                      <div class="pantone-name">{{ color.name }}</div>
                      <div class="pantone-hex">{{ color.hex }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="palette-block warning-block">
                <h3><el-icon><Close /></el-icon> 建议避雷色</h3>
                <div class="color-list">
                  <div class="color-item avoid" v-for="(color, index) in mockResult.avoidColors" :key="index">
                    <div class="color-box line-through" :style="{ backgroundColor: color.hex }"></div>
                    <span class="color-name">{{ color.name }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="action-footer">
          <el-button class="gradient-btn" size="large" @click="goToMakeup">
            根据季型生成专属男妆 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ModernBackground from '../components/ModernBackground.vue'
import { UserFilled, Check, Close, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const uploadedImage = ref('')

onMounted(() => {
  // 从上传页面接收临时图片 URL
  if (route.query.img) {
    uploadedImage.value = route.query.img as string
  }
})

// Mock PCA 数据
const mockResult = {
  season: '温润秋季型',
  description: '您的面部色彩重心偏暖且柔和，呈现出如成熟秋枫般稳重、深邃的质感。适合带有大地色调、低饱和度却具有包容感的色彩，能完美衬托出男性内敛且高级的魅力。',
  recommendedColors: [
    { name: '大地棕', hex: '#6D4C41', pantone: '19-1420 TCX' },
    { name: '枫叶红', hex: '#D84315', pantone: '17-1462 TCX' },
    { name: '橄榄绿', hex: '#558B2F', pantone: '18-0328 TCX' },
    { name: '暖驼色', hex: '#D7CCC8', pantone: '13-1008 TCX' }
  ],
  avoidColors: [
    { name: '冷荧光粉', hex: '#FF4081' },
    { name: '正蓝色', hex: '#2196F3' },
    { name: '纯亮紫', hex: '#9C27B0' }
  ]
}

const goToMakeup = () => {
  // 跳转到现有的最终合成页，把图片继续带过去
  router.push({
    name: 'Result',
    query: {
      img: uploadedImage.value,
      season: mockResult.season // 可以附带季型参数供后续使用
    }
  })
}
</script>

<style scoped>
.pca-container {
  min-height: 100vh;
  position: relative;
  overflow-y: auto;
  color: #1e293b;
  font-family: 'Outfit', sans-serif;
}

.content-wrapper {
  position: relative;
  z-index: 1;
  max-width: 1000px;
  margin: 0 auto;
  padding: 80px 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}

.glass-panel {
  width: 100%;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  padding: 50px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.05);
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.title {
  text-align: center;
  font-size: 32px;
  font-weight: 800;
  color: #2E7D32;
  margin-bottom: 12px;
}

.subtitle {
  text-align: center;
  color: #64748b;
  font-size: 16px;
  margin-bottom: 50px;
}

.report-content {
  display: flex;
  gap: 50px;
  align-items: center;
}

/* Avatar Section */
.avatar-section {
  flex: 0 0 350px;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.avatar-frame {
  width: 320px;
  height: 420px;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
  background: #f1f5f9;
  display: flex;
  justify-content: center;
  align-items: center;
  border: 8px solid white;
}

.avatar-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder-avatar {
  font-size: 64px;
  color: #cbd5e1;
}

.avatar-badge {
  position: absolute;
  bottom: -15px;
  background: #2E7D32;
  color: white;
  padding: 8px 24px;
  border-radius: 30px;
  font-weight: 600;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(46, 125, 50, 0.3);
  border: 2px solid white;
}

/* Result Section */
.result-section {
  flex: 1;
}

.season-badge {
  display: inline-flex;
  align-items: center;
  background: #E8F5E9;
  border-radius: 12px;
  padding: 10px 20px;
  margin-bottom: 20px;
}

.season-badge .label {
  color: #2E7D32;
  font-weight: 600;
  margin-right: 12px;
  font-size: 14px;
}

.season-badge .value {
  font-size: 24px;
  font-weight: 800;
  color: #1a1a1a;
  background: linear-gradient(135deg, #FF8F00, #E65100);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.season-desc {
  color: #475569;
  line-height: 1.8;
  font-size: 15px;
  margin-bottom: 40px;
}

.color-palette-group {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.palette-block h3 {
  font-size: 16px;
  font-weight: 600;
  color: #2E7D32;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.warning-block h3 {
  color: #ef4444;
}

.color-list {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

/* Pantone Card Styles */
.pantone-list {
  gap: 20px;
}

.pantone-card {
  width: 100px;
  height: 140px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
  border: 1px solid #f1f5f9;
}

.pantone-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 12px 25px rgba(0, 0, 0, 0.12);
}

.pantone-color-area {
  flex: 1;
  width: 100%;
}

.pantone-info-area {
  height: 55px;
  padding: 6px 8px;
  background: white;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.pantone-title {
  font-size: 8px;
  font-weight: 800;
  color: #1a1a1a;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}

.pantone-code {
  font-size: 10px;
  font-weight: 700;
  color: #1a1a1a;
}

.pantone-name {
  font-size: 9px;
  font-weight: 500;
  color: #64748b;
  margin-top: 1px;
}

.pantone-hex {
  font-size: 8px;
  color: #94a3b8;
  font-family: monospace;
  margin-top: 1px;
}

/* Original Color Item (Used for Avoid Colors) */
.color-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.color-box {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.08);
  transition: transform 0.3s;
  position: relative;
  overflow: hidden;
}

.color-box.line-through::after {
  content: '';
  position: absolute;
  top: 50%;
  left: -20%;
  width: 140%;
  height: 3px;
  background-color: rgba(255, 255, 255, 0.8);
  transform: rotate(-45deg);
}

.color-item:hover .color-box {
  transform: translateY(-5px) scale(1.05);
}

.color-name {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

/* Action Footer */
.action-footer {
  margin-top: 60px;
  text-align: center;
}

.gradient-btn {
  background: #2E7D32 !important;
  color: white !important;
  border: none;
  border-radius: 50px;
  padding: 15px 40px;
  font-size: 18px;
  font-weight: 600;
  height: auto;
  box-shadow: 0 10px 25px rgba(46, 125, 50, 0.25);
  transition: all 0.3s;
}

.gradient-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 15px 35px rgba(46, 125, 50, 0.35);
  background: #1b5e20 !important;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 900px) {
  .report-content {
    flex-direction: column;
  }
  .avatar-section {
    flex: 0 0 auto;
  }
  .glass-panel {
    padding: 30px;
  }
}
</style>
