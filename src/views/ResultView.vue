<template>
  <div class="result-view-container">
    <div class="main-layout">
      <!-- Left Core Work Area -->
      <div class="work-area">
        <div class="header-bar">
          <el-steps :active="activeStep" finish-status="success" simple>
            <el-step title="上传图片" />
            <el-step title="智能矫正" />
            <el-step title="风格美妆" />
          </el-steps>
        </div>

        <!-- Canvas / Image Comparison -->
        <div class="canvas-container" v-loading="processing" :element-loading-text="loadingText">
          <div v-if="!currentResultImage" class="single-image">
            <img :src="originalImage" alt="Original" v-if="originalImage" />
            <div v-else class="empty-state">
              <el-empty description="未检测到图片，请返回上传">
                <el-button type="primary" @click="router.push('/upload')">去上传</el-button>
              </el-empty>
            </div>
          </div>
          <ImageComparison 
            v-else 
            :before-image="originalImage" 
            :after-image="currentResultImage" 
          />
        </div>

        <!-- Quick Operations -->
        <div class="operation-bar" v-if="currentResultImage">
          <el-button icon="Back" @click="handleUndo" :disabled="!canUndo">撤销上一步</el-button>
          <el-button icon="Refresh" @click="handleReset">重置妆容</el-button>
          <el-button icon="Download" @click="handleMainDownloadClick">导出原图</el-button>
        </div>

        <!-- Bottom Navigation Toolbar -->
        <div class="bottom-nav">
          <div class="nav-left">
            <span class="nav-label">一键妆容</span>
            <el-select v-model="params.style" placeholder="选择风格" class="style-select" size="large">
              <el-option label="自然清透" value="clean" />
              <el-option label="轻熟职场" value="business" />
              <el-option label="韩系潮流" value="idol" />
            </el-select>
            <el-button type="success" plain @click="handleApplyFullStyle" :loading="processingStyle" size="large" class="quick-btn">
              全妆渲染
            </el-button>
          </div>
          
          <div class="nav-middle">
            <el-radio-group v-model="currentMakeupStep" class="makeup-steps" size="large">
              <el-radio-button label="base">底妆</el-radio-button>
              <el-radio-button label="eyebrow">眉毛</el-radio-button>
              <el-radio-button label="eye">眼妆</el-radio-button>
              <el-radio-button label="contour">修容</el-radio-button>
              <el-radio-button label="lip">唇部</el-radio-button>
            </el-radio-group>
          </div>

          <div class="nav-right">
            <el-button type="primary" class="generate-btn" @click="handleApplyStep" :loading="processingStep" size="large">
              单独渲染该步骤
            </el-button>
          </div>
        </div>
      </div>

      <!-- Right Sidebar Area -->
      <div class="sidebar-area">
        <div class="sidebar-header">
          <h3>本季专属推荐</h3>
          <div class="season-tag">{{ userSeason }}</div>
        </div>

        <div class="product-list-container">
          <div class="product-item" v-for="product in mockProducts" :key="product.id" @click="goToShopItem(product.id)">
            <div class="product-img">
              <img :src="product.img" alt="product" />
            </div>
            <div class="product-info">
              <div class="p-category">{{ product.category }}</div>
              <div class="p-name">{{ product.name }}</div>
              <div class="p-color">色号: {{ product.color }}</div>
            </div>
          </div>
        </div>

        <div class="sidebar-footer">
          <div v-if="planSaved" class="saved-plan-area">
            <el-alert title="方案已保存至个人中心" type="success" :closable="false" show-icon class="save-alert" />
            <el-button type="danger" class="buy-all-btn" @click="goToShop">一键购齐搭配单品</el-button>
          </div>
          <el-button v-else type="primary" class="save-plan-btn" @click="savePlan">
            保存当前方案
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ImageComparison from '../components/ImageComparison.vue'
import { Back, Refresh, Download } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const originalImage = ref('')
const currentResultImage = ref('')
const activeStep = ref(2)
const processing = ref(false)
const processingStyle = ref(false)
const processingStep = ref(false)
const loadingText = ref('')

const params = ref({
  style: 'clean'
})

// Sub-step makeup 
const currentMakeupStep = ref('base')
const canUndo = ref(false)

// User PCA Season passed from previous page
const userSeason = ref('温润秋季型')

// Mock Products related to season/style
const mockProducts = ref([
  { id: 101, category: '底妆', name: '极光无瑕粉底液', color: '自然偏白', img: 'https://images.unsplash.com/photo-1599305090598-fe179d501227?w=150&q=80' },
  { id: 102, category: '眉毛', name: '立体塑形眉粉组合', color: '深棕灰', img: 'https://images.unsplash.com/photo-1629198688000-71f23e745b6e?w=150&q=80' },
  { id: 103, category: '眼妆', name: '深秘大地四色眼影', color: '大地色系', img: 'https://images.unsplash.com/photo-1583241494208-1c4db21c97a5?w=150&q=80' },
  { id: 104, category: '修容', name: '自然立体修容高光盘', color: '灰棕色', img: 'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=150&q=80' },
  { id: 105, category: '唇部', name: '哑光丝绒裸色唇釉', color: '枯玫瑰色', img: 'https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=150&q=80' }
])

const planSaved = ref(false)

onMounted(() => {
  const img = route.query.img as string
  const season = route.query.season as string

  if (img) {
    originalImage.value = img
    activeStep.value = 2
    currentResultImage.value = ''
    ElMessage.success('已就绪，请选择想要叠加的妆容或风格')
  }
  
  if (season) {
    userSeason.value = season
  }
})

const handleUndo = () => {
  ElMessage.info('已撤销上一步操作')
  canUndo.value = false
}

const handleReset = () => {
  activeStep.value = 2
  currentResultImage.value = ''
  params.value.style = 'clean'
  canUndo.value = false
  planSaved.value = false
}

// 模拟分离：一键全妆渲染
const handleApplyFullStyle = async () => {
  if (activeStep.value < 2) return
  
  processingStyle.value = true
  processing.value = true
  
  const styleNameMap: Record<string, string> = {
    clean: '自然清透', business: '轻熟职场', idol: '韩系潮流'
  }
  const currentStyle = styleNameMap[params.value.style] || '专属'
  
  loadingText.value = `正在进行【一键全妆】渲染，应用${currentStyle}风格...`
  
  try {
    await new Promise(resolve => setTimeout(resolve, 2000))
    currentResultImage.value = originalImage.value 
    
    activeStep.value = 3
    canUndo.value = true
    ElMessage.success(`全脸风格渲染完成！您可以继续局部微调或直接保存方案。`)
  } catch (error: any) {
    ElMessage.error(`生成失败: ${error.message}`)
  } finally {
    processingStyle.value = false
    processing.value = false
  }
}

// 模拟分离：精细单步渲染
const handleApplyStep = async () => {
  if (activeStep.value < 2) return
  
  processingStep.value = true
  processing.value = true

  const stepNameMap: Record<string, string> = {
    base: '底妆', eyebrow: '眉毛', eye: '眼妆', contour: '修容', lip: '唇部'
  }
  const currentPart = stepNameMap[currentMakeupStep.value] || '部分'
  
  loadingText.value = `正在精准渲染局部：叠加[${currentPart}]效果...`
  
  try {
    await new Promise(resolve => setTimeout(resolve, 1500))
    currentResultImage.value = originalImage.value 
    
    activeStep.value = 3
    canUndo.value = true
    ElMessage.success(`局部 [${currentPart}] 处理叠加完成！`)
  } catch (error: any) {
    ElMessage.error(`生成失败: ${error.message}`)
  } finally {
    processingStep.value = false
    processing.value = false
  }
}

const handleMainDownloadClick = () => {
  if (!currentResultImage.value) {
    ElMessage.warning('暂无可以下载的渲染图')
    return
  }
  ElMessage.success('原图下载已开始...')
}

const savePlan = () => {
  if (!currentResultImage.value) {
    ElMessage.warning('请先生成一个满意的叠加妆容再保存方案')
    return
  }
  planSaved.value = true
  ElMessage.success('方案已成功保存至个人档案！')
}

const goToShop = () => {
  router.push('/shop')
}

const goToShopItem = (id: number) => {
  ElMessage.success(`模拟跳转到商城单品 (SKU ID: ${id}) 详情页`)
  router.push('/shop')
}
</script>

<style scoped>
/* Core Layout Themes */
.result-view-container {
  min-height: 100vh;
  /* Light Theme Background matching Home */
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 30px;
  color: #1e293b;
  font-family: 'Outfit', sans-serif;
  display: flex;
  justify-content: center;
}

.main-layout {
  display: flex;
  gap: 25px;
  width: 100%;
  max-width: 1400px;
  height: calc(100vh - 60px);
}

/* Left Workspace */
.work-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(15px);
  border-radius: 20px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
  overflow: hidden;
  padding: 24px;
}

.header-bar {
  margin-bottom: 20px;
}
.header-bar :deep(.el-steps--simple) {
  background: transparent;
  padding: 10px 0;
}

.canvas-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f1f5f9;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  border: 1px solid #e2e8f0;
}

.single-image {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.single-image img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

/* Operations */
.operation-bar {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 20px;
}

/* Bottom Nav */
.bottom-nav {
  margin-top: 20px;
  background: white;
  border-radius: 16px;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 15px rgba(0,0,0,0.03);
  border: 1px solid #e2e8f0;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-label {
  font-weight: 600;
  color: #475569;
}

.style-select {
  width: 120px;
}

.quick-btn {
  margin-left: 10px;
  font-weight: 600;
}

.nav-middle {
  flex: 1;
  display: flex;
  justify-content: center;
}

.generate-btn {
  background: #2E7D32 !important;
  border-color: #2E7D32 !important;
  border-radius: 12px;
  padding: 10px 30px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(46, 125, 50, 0.2);
}

.generate-btn:hover {
  background: #1b5e20 !important;
}

/* Right Sidebar */
.sidebar-area {
  width: 380px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(15px);
  border-radius: 20px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 24px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
}

.season-tag {
  background: #E8F5E9;
  color: #2E7D32;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}

.product-list-container {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.product-item {
  display: flex;
  gap: 16px;
  background: white;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #f1f5f9;
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: pointer;
}

.product-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.06);
}

.product-img {
  width: 70px;
  height: 70px;
  border-radius: 8px;
  overflow: hidden;
  background: #f8fafc;
}

.product-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.p-category {
  font-size: 12px;
  color: #2E7D32;
  font-weight: 600;
  margin-bottom: 4px;
}

.p-name {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 4px;
}

.p-color {
  font-size: 13px;
  color: #94a3b8;
}

.sidebar-footer {
  padding: 24px;
  border-top: 1px solid #e2e8f0;
  background: #fff;
}

.save-plan-btn {
  width: 100%;
  height: 50px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  background: #1a1a1a;
  color: #fff;
  border: none;
  transition: background 0.3s;
}

.save-plan-btn:hover {
  background: #333;
}

.saved-plan-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.save-alert {
  margin: 0;
}

.buy-all-btn {
  width: 100%;
  height: 50px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  background: #e11d48;
  color: #fff;
  border: none;
  transition: background 0.3s;
}

.buy-all-btn:hover {
  background: #be123c;
}
</style>
