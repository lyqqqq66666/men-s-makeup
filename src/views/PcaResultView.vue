<template>
  <div class="pca-container">
    <ModernBackground />
    
    <div class="content-wrapper">
      <div class="glass-panel">
        <div class="back-btn-wrapper-pca">
          <el-button link :icon="ArrowLeft" @click="router.back()" class="custom-back-btn">
            返回上一页
          </el-button>
        </div>
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

            <div class="features-block">
              <h3><el-icon><Star /></el-icon> 专属风格与特征</h3>
              <ul>
                <li v-for="(feature, index) in mockResult.features" :key="index">{{ feature }}</li>
              </ul>
            </div>

            <div class="color-palette-group">
              <div class="palette-block">
                <h3><el-icon><Check /></el-icon> 推荐专属色 (PANTONE® 分子式)</h3>
                <div class="color-list pantone-list">
                  <div 
                    class="pantone-card clickable-card" 
                    v-for="(color, index) in mockResult.recommendedColors" 
                    :key="index"
                    @click="goToShopWithColor(color.filterKey)"
                  >
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
            </div>

            <div class="recommended-products-block" v-if="mockResult.recommendedProducts && mockResult.recommendedProducts.length > 0">
              <h3><el-icon><Goods /></el-icon> 为您优选试妆商品</h3>
              <div class="mini-products-list">
                <div class="mini-product-card" v-for="product in mockResult.recommendedProducts" :key="product.id" @click="goToShopWithColor('')">
                  <img :src="product.image" class="mini-product-img" />
                  <div class="mini-product-info">
                    <div class="mini-product-name">{{ product.name }}</div>
                    <div class="mini-product-price">¥{{ product.price }}</div>
                    <div class="mini-product-tags">
                      <el-tag size="small" type="warning" effect="dark" v-for="tag in product.tags" :key="tag">{{ tag }}</el-tag>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="action-footer">
          <el-button class="action-btn primary-btn" size="large" @click="goToShopWithColor('')">
            立即查看适合商品 <el-icon class="el-icon--right"><ShoppingBag /></el-icon>
          </el-button>
          <el-button class="action-btn secondary-btn" size="large" @click="goToMakeup">
            一键试用推荐妆容 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
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
import { UserFilled, Check, ArrowRight, ArrowLeft, Star, Goods, ShoppingBag } from '@element-plus/icons-vue'

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
  seasonKey: 'autumn', // 用于向商城传递的季型枚举值
  season: '温润秋季型',
  description: '您的面部色彩重心偏暖且柔和，呈现出如成熟秋枫般稳重、深邃的质感。适合带有大地色调、低饱和度却具有包容感的色彩，能完美衬托出男性内敛且高级的魅力。',
  features: [
    '底妆建议：选择自然偏暖、哑光质地的粉底，避免假白。',
    '眉毛建议：深棕色或灰褐色，强调毛流感，避免纯黑生硬线条。',
    '穿搭色彩：大地色系、卡其色、军绿色等低亮度暖色。'
  ],
  recommendedColors: [
    { name: '大地棕', hex: '#6D4C41', pantone: '19-1420 TCX', filterKey: 'neutral' },
    { name: '枫叶红', hex: '#D84315', pantone: '17-1462 TCX', filterKey: 'warm' },
    { name: '橄榄绿', hex: '#558B2F', pantone: '18-0328 TCX', filterKey: 'neutral' },
    { name: '暖驼色', hex: '#D7CCC8', pantone: '13-1008 TCX', filterKey: 'neutral' }
  ],
  recommendedProducts: [
    { id: 4, name: '自然色男士BB霜', price: '189', image: new URL('../assets/products/bb_cream.jpg', import.meta.url).href, tags: ['PCA推荐', '热门试妆'] },
    { id: 6, name: '男士眉笔 (深棕灰)', price: '59', image: new URL('../assets/products/eyebrow_pencil.jpg', import.meta.url).href, tags: ['PCA推荐', '新手友好'] }
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

const goToShopWithColor = (colorFilterKey: string) => {
  router.push({
    path: '/shop',
    query: {
      season: mockResult.seasonKey,
      color: colorFilterKey || undefined
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 80px 20px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: 100vh;
}

.glass-panel {
  width: 100%;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 40px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
  position: relative;
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.back-btn-wrapper-pca {
  position: absolute;
  top: 24px;
  left: 30px;
}

.custom-back-btn {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
  transition: all 0.3s ease;
}

.custom-back-btn:hover {
  color: #3b82f6;
  transform: translateX(-2px);
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
  align-items: flex-start;
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
  min-width: 0;
  word-wrap: break-word;
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

.clickable-card {
  cursor: pointer;
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

/* Features & Products additions */
.features-block {
  margin-bottom: 30px;
  background: #F8FAFC;
  padding: 20px;
  border-radius: 12px;
  border-left: 4px solid #2E7D32;
}

.features-block h3 {
  font-size: 16px;
  font-weight: 600;
  color: #2E7D32;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.features-block ul {
  padding-left: 20px;
  margin: 0;
  color: #475569;
  font-size: 14px;
  line-height: 1.8;
}

.recommended-products-block {
  margin-top: 40px;
}

.recommended-products-block h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mini-products-list {
  display: flex;
  gap: 15px;
}

.mini-product-card {
  display: flex;
  align-items: center;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  width: 260px;
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s, border-color 0.3s;
}

.mini-product-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 20px rgba(0,0,0,0.06);
  border-color: #2E7D32;
}

.mini-product-img {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  object-fit: cover;
  margin-right: 12px;
}

.mini-product-info {
  flex: 1;
}

.mini-product-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 150px;
}

.mini-product-price {
  font-size: 15px;
  font-weight: 700;
  color: #E65100;
  margin-bottom: 6px;
}

.mini-product-tags {
  display: flex;
  gap: 4px;
}
.mini-product-tags .el-tag {
  font-size: 10px;
  padding: 0 4px;
  height: 20px;
  line-height: 18px;
}

/* Action Footer */
.action-footer {
  margin-top: 50px;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.action-btn {
  border-radius: 50px;
  padding: 15px 40px;
  font-size: 16px;
  font-weight: 600;
  height: auto;
  transition: all 0.3s;
}

.primary-btn {
  background: #2E7D32 !important;
  color: white !important;
  border: none;
  box-shadow: 0 10px 25px rgba(46, 125, 50, 0.25);
}

.primary-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 15px 35px rgba(46, 125, 50, 0.35);
  background: #1b5e20 !important;
}

.secondary-btn {
  background: white !important;
  color: #2E7D32 !important;
  border: 2px solid #2E7D32 !important;
}

.secondary-btn:hover {
  background: #f8fafc !important;
  transform: translateY(-3px);
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
