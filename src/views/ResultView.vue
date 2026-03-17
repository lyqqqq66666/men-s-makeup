<template>
  <div class="result-view-container">
    <div class="main-layout">
      <!-- Left Core Work Area -->
      <div class="work-area">
        <div class="back-btn-wrapper-result">
          <el-button link :icon="ArrowLeft" @click="router.back()" class="custom-back-btn">
            返回上一页
          </el-button>
        </div>
        <div class="header-bar">
          <div class="step-indicator">
            <span class="step-count">Step {{ currentStepIndex }}/5</span>
            <span class="step-name">{{ currentStepName }}</span>
          </div>
          <el-steps :active="activeStep" finish-status="success" simple>
            <el-step title="上传图片" />
            <el-step title="智能矫正" />
            <el-step title="风格美妆" />
          </el-steps>
        </div>
        
        <div class="recommendation-tip" v-if="activeStep >= 2">
          <el-icon><Star /></el-icon> {{ stepRecommendation }}
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
          <el-button :icon="Back" @click="handleUndo" :disabled="!canUndo">撤销上一步</el-button>
          <el-button :icon="Close" @click="handleRevertStep">卸除本步局妆</el-button>
          <el-button :icon="Refresh" @click="handleFullClean" type="danger" plain>一键卸脸</el-button>
          <el-button :icon="Download" @click="handleMainDownloadClick">导出原图</el-button>
        </div>

        <!-- Bottom Navigation Toolbar -->
        <div class="bottom-nav">
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
            <el-button type="primary" class="generate-btn" @click="handleApplyStep(null)" :loading="processingStep" size="large">
              执行{{ currentStepName }}
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

        <div class="style-presets">
          <div class="preset-label">懒人一键渲染</div>
          <div class="preset-buttons">
            <el-button size="small" @click="params.style='clean'; handleApplyFullStyle()" :loading="processingStyle && params.style==='clean'">自然清透</el-button>
            <el-button size="small" @click="params.style='business'; handleApplyFullStyle()" :loading="processingStyle && params.style==='business'">轻熟职场</el-button>
            <el-button size="small" @click="params.style='idol'; handleApplyFullStyle()" :loading="processingStyle && params.style==='idol'">韩系潮流</el-button>
          </div>
        </div>

        <div class="applied-list" v-if="Object.keys(appliedProducts).length > 0">
          <div class="applied-label">已上脸单品：</div>
          <div class="applied-items">
            <div class="applied-item" v-for="(prod, step) in appliedProducts" :key="step">
              <img :src="prod.img" :title="prod.name" />
            </div>
          </div>
        </div>

        <div class="product-list-container">
          <div 
            class="product-item" 
            v-for="product in filteredProducts" 
            :key="product.id" 
            :class="{ 'is-selected': appliedProducts[currentMakeupStep]?.id === product.id }"
            @click="handleApplyStep(product)"
          >
            <div class="product-img">
              <img :src="product.img" alt="product" />
            </div>
            <div class="product-info">
              <div class="p-category">{{ product.category }}</div>
              <div class="p-name">{{ product.name }}</div>
              <div class="p-color">色号: {{ product.color }}</div>
            </div>
            <div class="selected-badge" v-if="appliedProducts[currentMakeupStep]?.id === product.id">
              <el-icon><Check /></el-icon>
            </div>
          </div>
        </div>

        <!-- 智能推荐引擎位置 A：试妆页插入 -->
        <div class="recommend-engine-card">
          <div class="rec-header">
            <h4><el-icon><StarFilled /></el-icon> 智能推荐套装</h4>
            <span class="rec-tag">日常通勤</span>
          </div>
          <div class="rec-content">
            <div class="rec-products">
              <div class="rec-item" v-for="(prod, idx) in mockProducts.slice(0, 3)" :key="idx">
                <img :src="prod.img" alt="推荐单品">
              </div>
              <div class="rec-count">+3件包含单品</div>
            </div>
            <div class="rec-actions">
              <el-button size="small" type="primary" plain @click="applyRecommendSet" :loading="processingStyle">一键渲染</el-button>
              <el-button size="small" type="danger" @click="buyRecommendSet">一键购齐</el-button>
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
      <!-- Save Plan Dialog -->
      <el-dialog v-model="savePlanDialogVisible" title="保存方案到个人形象方案库" width="400px" class="save-plan-dialog">
        <el-form label-position="top">
          <el-form-item label="方案名称">
            <el-input v-model="planForm.name" placeholder="起个响亮的方案名" />
          </el-form-item>
          <el-form-item label="专属场景打标">
            <el-select v-model="planForm.scene" placeholder="选择适合的场景" style="width: 100%;">
              <el-option label="日常通勤" value="日常通勤" />
              <el-option label="面试清爽" value="面试清爽" />
              <el-option label="约会氛围" value="约会氛围" />
              <el-option label="商务稳重" value="商务稳重" />
              <el-option label="新手低门槛" value="新手低门槛" />
            </el-select>
          </el-form-item>
          <el-form-item label="推荐理由备忘">
            <el-input type="textarea" v-model="planForm.reason" :rows="3" placeholder="写几句提醒自己的理由..." />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="savePlanDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="confirmSavePlan">
              入库保存
            </el-button>
          </span>
        </template>
      </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ImageComparison from '../components/ImageComparison.vue'
import { Back, Refresh, Download, Star, Check, Close, StarFilled, ArrowLeft } from '@element-plus/icons-vue'

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

const makeupStepsOrder = ['base', 'eyebrow', 'eye', 'contour', 'lip']
const stepNameMap: Record<string, string> = {
  base: '底妆', eyebrow: '眉毛', eye: '眼妆', contour: '修容', lip: '唇部'
}

const currentStepIndex = computed(() => {
  return makeupStepsOrder.indexOf(currentMakeupStep.value) + 1
})

const currentStepName = computed(() => {
  return stepNameMap[currentMakeupStep.value] || '部分'
})

const stepRecommendation = computed(() => {
  const recs: Record<string, string> = {
    base: '建议从最贴近肤色的粉底开始，打造清透无瑕的男士自然底妆。',
    eyebrow: '推荐使用深灰或灰棕色，顺着毛流方向自然填补，避免边缘过硬。',
    eye: '男士眼妆宜极简，建议仅用大地色在眼尾或眼圈周围微微加深轮廓即可。',
    contour: '重点打在鼻梁两侧与下颌线处，可以极大提升五官折叠度。',
    lip: '尽量选择低饱和度的哑光口红，只做提色，不要油腻反光。'
  }
  return recs[currentMakeupStep.value] || '根据您的季型推荐适合的单品。'
})

// Store applied products for each step by stepKey
const appliedProducts = ref<Record<string, any>>({})

// User PCA Season passed from previous page
const userSeason = ref('温润秋季型')

// Mock Products related to season/style
const mockProducts = ref([
  { id: 101, category: '底妆', stepKey: 'base', name: '极光无瑕粉底液', color: '自然偏白', img: 'https://images.unsplash.com/photo-1599305090598-fe179d501227?w=150&q=80' },
  { id: 102, category: '眉毛', stepKey: 'eyebrow', name: '立体塑形眉粉组合', color: '深棕灰', img: 'https://images.unsplash.com/photo-1629198688000-71f23e745b6e?w=150&q=80' },
  { id: 103, category: '眼妆', stepKey: 'eye', name: '深秘大地四色眼影', color: '大地色系', img: 'https://images.unsplash.com/photo-1583241494208-1c4db21c97a5?w=150&q=80' },
  { id: 104, category: '修容', stepKey: 'contour', name: '自然立体修容高光盘', color: '灰棕色', img: 'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=150&q=80' },
  { id: 105, category: '唇部', stepKey: 'lip', name: '哑光丝绒裸色唇釉', color: '枯玫瑰色', img: 'https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=150&q=80' },
  { id: 106, category: '底妆', stepKey: 'base', name: '控油持妆男士粉底液', color: '健康小麦', img: 'https://images.unsplash.com/photo-1599305090598-fe179d501227?w=150&q=80' },
  { id: 107, category: '唇部', stepKey: 'lip', name: '轻感滋润男士润唇膏', color: '素颜粉', img: 'https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=150&q=80' }
])

const filteredProducts = computed(() => {
  return mockProducts.value.filter(p => p.stepKey === currentMakeupStep.value)
})

const planSaved = ref(false)

onMounted(() => {
  const img = route.query.img as string
  const season = route.query.season as string

  if (img) {
    originalImage.value = img
    activeStep.value = 2
    currentResultImage.value = ''
    ElMessage.success('已优先为您推荐一套最自然的底妆，请确认')
    
    // Default apply base product
    const defaultBase = mockProducts.value.find(p => p.stepKey === 'base')
    if (defaultBase) {
      appliedProducts.value['base'] = defaultBase
    }
  }
  
  if (season) {
    userSeason.value = season
  }
})

const handleUndo = () => {
  ElMessage.info('已撤销上一步操作')
  canUndo.value = false
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
    
    // Auto-select items in sidebar to show they are applied
    appliedProducts.value['base'] = mockProducts.value.find(p => p.stepKey === 'base') || appliedProducts.value['base']
    appliedProducts.value['eyebrow'] = mockProducts.value.find(p => p.stepKey === 'eyebrow') || appliedProducts.value['eyebrow']
    appliedProducts.value['lip'] = mockProducts.value.find(p => p.stepKey === 'lip') || appliedProducts.value['lip']
    
    ElMessage.success(`全脸风格渲染完成！您可以继续局部微调或直接保存方案。`)
  } catch (error: any) {
    ElMessage.error(`生成失败: ${error.message}`)
  } finally {
    processingStyle.value = false
    processing.value = false
  }
}

// 模拟分离：精细单步渲染 (配合商品应用)
const handleApplyStep = async (product?: any) => {
  if (activeStep.value < 2) return
  
  processingStep.value = true
  processing.value = true

  const currentPart = stepNameMap[currentMakeupStep.value] || '部分'
  
  loadingText.value = `正在精准渲染局部：叠加[${currentPart}]效果...`
  
  try {
    await new Promise(resolve => setTimeout(resolve, 1500))
    currentResultImage.value = originalImage.value 
    
    // 记录已应用的商品
    if (product) {
      appliedProducts.value[currentMakeupStep.value] = product
    }

    activeStep.value = 3
    canUndo.value = true
    
    // 如果不是最后一步，引导去下一步
    if (currentStepIndex.value < 5) {
      currentMakeupStep.value = makeupStepsOrder[currentStepIndex.value] as string
      ElMessage.success(`局部 [${currentPart}] 处理完成！已自动切入下一步装扮。`)
    } else {
      ElMessage.success(`局部 [${currentPart}] 处理完成！这是最后一步了。`)
    }

  } catch (error: any) {
    ElMessage.error(`生成失败: ${error.message}`)
  } finally {
    processingStep.value = false
    processing.value = false
  }
}

// 卸载单步妆容
const handleRevertStep = () => {
  if (appliedProducts.value[currentMakeupStep.value]) {
    delete appliedProducts.value[currentMakeupStep.value]
    ElMessage.success(`已卸去当前的【${currentStepName.value}】。`)
  } else {
    ElMessage.warning(`尚未应用【${currentStepName.value}】相关的商品。`)
  }
}

// 一键完全卸妆
const handleFullClean = () => {
  appliedProducts.value = {}
  activeStep.value = 2
  currentResultImage.value = ''
  canUndo.value = false
  ElMessage.success('全脸卸妆完毕，已重置为素颜状态。')
}

const handleMainDownloadClick = () => {
  if (!currentResultImage.value) {
    ElMessage.warning('暂无可以下载的渲染图')
    return
  }
  ElMessage.success('原图下载已开始...')
}

const savePlanDialogVisible = ref(false)
const planForm = ref({
  name: '',
  scene: '',
  reason: ''
})

const savePlan = () => {
  if (!currentResultImage.value) {
    ElMessage.warning('请先生成一个满意的叠加妆容再保存方案')
    return
  }
  savePlanDialogVisible.value = true
}

// 推荐引擎：一键购齐
const buyRecommendSet = () => {
  ElMessage.success('已将《智能推荐套装》内的 3 件单品打包加入购物车！')
}

// 推荐引擎：一键渲染
const applyRecommendSet = () => {
  params.value.style = 'clean'
  handleApplyFullStyle()
}

const confirmSavePlan = () => {
  if (!planForm.value.name || !planForm.value.scene) {
    ElMessage.warning('请填写完整的名称及选择对应场景标签！')
    return
  }
  planSaved.value = true
  savePlanDialogVisible.value = false
  ElMessage.success('方案已作为数字资产入库！您可前往个人中心统一管理。')
}

const goToShop = () => {
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

.back-btn-wrapper-result {
  margin-bottom: 12px;
}

.custom-back-btn {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

.custom-back-btn:hover {
  color: #3b82f6;
  transform: translateX(-2px);
}

.header-bar {
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-bar :deep(.el-steps--simple) {
  background: transparent;
  padding: 10px 0;
  width: 60%;
}

.step-indicator {
  display: flex;
  flex-direction: column;
}
.step-count {
  font-size: 14px;
  color: #64748b;
  font-weight: 600;
}
.step-name {
  font-size: 24px;
  font-weight: 700;
  color: #2E7D32;
}

.recommendation-tip {
  margin-bottom: 20px;
  background: #E8F5E9;
  color: #1b5e20;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-left: 4px solid #2E7D32;
}

.canvas-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: stretch;
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

.style-presets {
  padding: 15px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: #fafafa;
}
.preset-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
  font-weight: 600;
}
.preset-buttons {
  display: flex;
  gap: 8px;
}

.applied-list {
  padding: 15px 24px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.applied-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}
.applied-items {
  display: flex;
  gap: 8px;
}
.applied-item {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #2E7D32;
}
.applied-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  cursor: pointer;
  position: relative;
}

.product-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.06);
}

.product-item.is-selected {
  border-color: #2E7D32;
  background: #f8fafc;
}

/* Recommend Engine Card */
.recommend-engine-card {
  margin: 0 20px 20px;
  background: linear-gradient(145deg, #ffffff, #f1f5f9);
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 15px rgba(0,0,0,0.03);
}

.rec-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.rec-header h4 {
  margin: 0;
  font-size: 14px;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 4px;
}

.rec-header .el-icon {
  color: #f59e0b;
}

.rec-tag {
  font-size: 11px;
  background: #e0e7ff;
  color: #4f46e5;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.rec-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rec-products {
  display: flex;
  align-items: center;
  gap: 6px;
}

.rec-item {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #cbd5e1;
}

.rec-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.rec-count {
  font-size: 12px;
  color: #64748b;
  margin-left: 4px;
}

.rec-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.selected-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: #2E7D32;
  color: white;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 12px;
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
