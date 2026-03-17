<template>
  <div class="shop-container">
    <ModernBackground />
    
    <div class="content-wrapper">
      <header class="header">
        <div class="logo" @click="router.push('/')">智颜方正</div>
        <div class="nav-actions">
          <el-button type="text" class="nav-btn" @click="router.push('/')">返回首页</el-button>
          
          <div class="cart-icon-wrapper" @click="drawerVisible = true">
            <el-badge :value="cart.length" :hidden="cart.length === 0" class="cart-badge">
              <el-button circle :icon="ShoppingCart" class="header-cart-btn"></el-button>
            </el-badge>
          </div>
        </div>
      </header>

      <main class="main-content">
        <div class="hero-section">
          <h1 class="page-title">适合你的商品推荐</h1>
          <p class="subtitle">根据你的季型和色系为你优先筛选</p>
        </div>

        <div class="filter-bar">
          <div class="filter-group">
            <span class="filter-label">季型</span>
            <el-select v-model="filterSeason" placeholder="全部" size="default" class="filter-select">
              <el-option label="全部" value="" />
              <el-option label="春季型" value="spring" />
              <el-option label="夏季型" value="summer" />
              <el-option label="秋季型" value="autumn" />
              <el-option label="冬季型" value="winter" />
            </el-select>
          </div>
          <div class="filter-group">
            <span class="filter-label">色系</span>
            <el-select v-model="filterColor" placeholder="全部" size="default" class="filter-select">
              <el-option label="全部" value="" />
              <el-option label="冷色调" value="cool" />
              <el-option label="暖色调" value="warm" />
              <el-option label="中性" value="neutral" />
            </el-select>
          </div>
          <div class="filter-group">
            <span class="filter-label">分类</span>
            <el-select v-model="filterCategory" placeholder="全部" size="default" class="filter-select">
              <el-option label="全部" value="" />
              <el-option label="护肤" value="skincare" />
              <el-option label="彩妆" value="makeup" />
              <el-option label="工具" value="tools" />
            </el-select>
          </div>
          <div class="filter-group">
            <span class="filter-label">排序</span>
            <el-select v-model="sortOrder" placeholder="推荐优先" size="default" class="filter-select">
              <el-option label="推荐优先" value="recommend" />
              <el-option label="价格从低到高" value="price_asc" />
              <el-option label="价格从高到低" value="price_desc" />
            </el-select>
          </div>
        </div>

        <div v-if="Object.keys(groupedProducts).length === 0" class="empty-state">
          <el-empty description="还没有找到合适的商品，先试试 AI 推荐妆容吧。">
            <el-button type="primary" @click="router.push('/upload')">去试试AI推荐妆容</el-button>
          </el-empty>
        </div>

        <div class="products-container" v-else>
          <div v-for="(group, category) in groupedProducts" :key="category" class="category-section">
            <h2 class="category-title">{{ getCategoryLabel(category) }}</h2>
            <div class="products-grid">
              <el-row :gutter="30">
                <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="item in getVisibleProducts(category, group)" :key="item.id">
                  <div class="product-card">
                    <div class="product-image">
                      <div class="product-img-container">
                        <img :src="item.image" :alt="item.name" class="real-product-img" />
                      </div>
                      <div class="sku-badge">{{ item.sku }}</div>
                      <div class="tags-container" v-if="item.tags && item.tags.length">
                        <el-tag
                          v-for="(tag, index) in item.tags.slice(0, 2)"
                          :key="index"
                          size="small"
                          effect="dark"
                          class="product-tag"
                          :type="tag === 'PCA推荐' ? 'warning' : 'info'"
                        >
                          {{ tag }}
                        </el-tag>
                      </div>
                      <div class="overlay">
                        <el-button type="primary" plain round @click="handleTryOn(item)">立即试用</el-button>
                      </div>
                    </div>
                    <div class="product-info">
                      <h3 class="product-name">{{ item.name }}</h3>
                      <div class="color-preview" v-if="item.colorHex">
                        <span class="color-dot" :style="{ backgroundColor: item.colorHex }"></span>
                        <span class="color-name">{{ item.colorName }}</span>
                      </div>
                      <p class="product-desc">{{ item.desc }}</p>
                      <div class="price-action-row">
                        <div class="product-price">¥{{ item.price }}</div>
                        <div class="sku-actions">
                          <el-button circle icon="ShoppingCart" @click="handleAddToCart(item)"></el-button>
                          <el-button type="primary" size="small" @click="handleTryOn(item)">立即试用</el-button>
                        </div>
                      </div>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>
            <div class="view-more-container" v-if="group.length > 4 && !expandedCategories[category as string]">
              <el-button plain round @click="expandedCategories[category as string] = true" class="view-more-btn">
                查看更多该类商品 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </main>

      <!-- Shopping Cart Drawer -->
      <el-drawer
        v-model="drawerVisible"
        title="我的购物车"
        direction="rtl"
        size="400px"
        custom-class="cart-drawer"
      >
        <div class="cart-content">
          <div v-if="cart.length === 0" class="empty-cart">
            <el-empty description="你的购物车还是空的，去看看适合你的热门商品吧。">
              <el-button type="primary" @click="drawerVisible = false">去逛逛</el-button>
            </el-empty>
          </div>
          <div v-else class="cart-items">
            <div v-for="(item, index) in cart" :key="index" class="cart-item">
              <img :src="item.image" class="cart-item-img" />
              <div class="cart-item-info">
                <div class="cart-item-name">{{ item.name }}</div>
                <div class="cart-item-sku">SKU: {{ item.sku }}</div>
                <div class="cart-item-price">¥{{ item.price }}</div>
              </div>
              <el-button
                type="danger"
                :icon="Delete"
                circle
                size="small"
                @click="removeFromCart(index)"
              />
            </div>
          </div>
        </div>
        <template #footer>
          <div class="cart-footer">
            <div class="total-price">
              <span>总计:</span>
              <span class="price-value">¥{{ totalPrice }}</span>
            </div>
            <el-button type="primary" size="large" class="checkout-btn" @click="handleCheckout" :disabled="cart.length === 0">
              立即结算
            </el-button>
          </div>
        </template>
      </el-drawer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ShoppingCart, Delete, ArrowDown } from '@element-plus/icons-vue'
import ModernBackground from '../components/ModernBackground.vue'

const router = useRouter()
const route = useRoute()

const filterSeason = ref('')
const filterColor = ref('')
const filterCategory = ref('')
const sortOrder = ref('recommend')

onMounted(() => {
  if (route.query.season) filterSeason.value = route.query.season as string
  if (route.query.color) filterColor.value = route.query.color as string
})

const expandedCategories = ref<Record<string, boolean>>({})

const products = [
  // tags, category, colorHex mocked data
  { id: 1, sku: 'S1-CLN', name: '男士焕能洁面乳', desc: '深层清洁，控油保湿', price: '129', image: new URL('../assets/products/cleanser.jpg', import.meta.url).href, category: 'skincare', tags: ['新手友好', '日常通勤'], season: 'all', colorType: 'neutral' },
  { id: 2, sku: 'S1-TNR', name: '清爽保湿爽肤水', desc: '收缩毛孔，醒肤补水', price: '159', image: new URL('../assets/products/toner.jpg', import.meta.url).href, category: 'skincare', tags: ['日常通勤'], season: 'all', colorType: 'neutral' },
  { id: 3, sku: 'S1-CRM', name: '多效修护面霜', desc: '抗皱紧致，滋润不油腻', price: '299', image: new URL('../assets/products/cream.jpg', import.meta.url).href, category: 'skincare', tags: ['PCA推荐', '热门试妆'], season: 'all', colorType: 'neutral' },
  { id: 4, sku: 'S2-BBC', name: '自然色男士BB霜', desc: '遮瑕修颜，持久不脱妆', price: '189', image: new URL('../assets/products/bb_cream.jpg', import.meta.url).href, category: 'makeup', colorHex: '#e8c39e', colorName: '自然偏白', tags: ['PCA推荐', '热门试妆'], season: 'spring', colorType: 'warm' },
  { id: 5, sku: 'S2-SPY', name: '定型喷雾', desc: '持久定型，清爽自然', price: '89', image: new URL('../assets/products/spray.jpg', import.meta.url).href, category: 'tools', tags: ['新手友好'], season: 'all', colorType: 'neutral' },
  { id: 6, sku: 'S2-BRW', name: '男士眉笔', desc: '立体塑形，防水防汗', price: '59', image: new URL('../assets/products/eyebrow_pencil.jpg', import.meta.url).href, category: 'makeup', colorHex: '#4a4036', colorName: '深棕灰', tags: ['PCA推荐', '新手友好'], season: 'winter', colorType: 'cool' },
  { id: 7, sku: 'S3-AFT', name: '须后舒缓乳', desc: '舒缓修护，清凉止痛', price: '119', image: new URL('../assets/products/aftershave.jpg', import.meta.url).href, category: 'skincare', tags: ['日常通勤'], season: 'all', colorType: 'neutral' },
  { id: 8, sku: 'S3-MSK', name: '男士专用面膜', desc: '深层补水，提亮肤色', price: '99', image: new URL('../assets/products/mask.jpg', import.meta.url).href, category: 'skincare', tags: ['热门试妆'], season: 'all', colorType: 'neutral' },
]

const getCategoryLabel = (cat: string | number) => {
  const map: Record<string, string> = {
    skincare: '护肤',
    makeup: '彩妆',
    tools: '工具'
  }
  return map[cat] || '其他'
}

const groupedProducts = computed(() => {
  // 1. 过滤
  let filtered = products.filter(p => {
    // mock mock seasons/color mappings 
    // Usually these are from backend or user's PCA record in real life, but we mock the filtering here.
    if (filterSeason.value && p.season !== 'all' && p.season !== filterSeason.value) return false
    if (filterColor.value && p.colorType !== 'neutral' && p.colorType !== filterColor.value) return false
    if (filterCategory.value && p.category !== filterCategory.value) return false
    return true
  })

  // 2. 排序
  filtered = filtered.sort((a, b) => {
    if (sortOrder.value === 'price_asc') return Number(a.price) - Number(b.price)
    if (sortOrder.value === 'price_desc') return Number(b.price) - Number(a.price)
    // recommend: we'll randomly place PCA推荐 at the top
    const aRec = a.tags.includes('PCA推荐') ? 1 : 0
    const bRec = b.tags.includes('PCA推荐') ? 1 : 0
    return bRec - aRec
  })

  // 3. 分组
  const groups: Record<string, typeof products> = {}
  filtered.forEach(p => {
    if (!groups[p.category]) {
      groups[p.category] = []
    }
    groups[p.category]!.push(p)
  })
  
  return groups
})

const getVisibleProducts = (category: string | number, items: any[]) => {
  if (expandedCategories.value[category]) {
    return items
  }
  return items.slice(0, 4)
}

const cart = ref<any[]>([])
const drawerVisible = ref(false)

const totalPrice = computed(() => {
  return cart.value.reduce((sum, item) => sum + Number(item.price), 0)
})

const handleAddToCart = (product: any) => {
  cart.value.push({ ...product })
  ElMessage.success(`已将【${product.name}】加入购物车`)
}

const removeFromCart = (index: number) => {
  const item = cart.value[index]
  cart.value.splice(index, 1)
  ElMessage.info(`已从购物车移除【${item.name}】`)
}

const handleCheckout = () => {
  ElMessage.success('结算功能正在开发中，即将跳转支付页面...')
}

const handleTryOn = (product: any) => {
  // Mock logic to determine if user has a stored photo
  // Here we use ElMessageBox to simulate the two states for the user to test
  ElMessageBox.confirm(
    '【前端模拟场景选择】当前用户在个人中心是否已经保存过照片？',
    '是否已有照片记录？',
    {
      distinguishCancelAndClose: true,
      confirmButtonText: '已保存过照片 (跳转试妆)',
      cancelButtonText: '没有照片 (引导上传)',
      type: 'info'
    }
  )
    .then(() => {
      // Flow 1: Has Photo -> Redirect to ResultView to render automatically
      ElMessage.success(`读取到个人照片记录，正在为您试用【${product.name}】...`)
      setTimeout(() => {
        router.push({
          path: '/result',
          query: {
            // we mock an img URL so the Result page has something to use as 'original'
            img: 'https://via.placeholder.com/600x800.png?text=Saved+User+Photo',
            auto_apply_product: product.id 
          }
        })
      }, 1000)
    })
    .catch((action) => {
      if (action === 'cancel') {
        // Flow 2: No Photo -> Redirect to UploadView
        ElMessage.warning('未检测到您的照片档案，请先上传照片。')
        setTimeout(() => {
          router.push('/upload')
        }, 1000)
      }
    })
}
</script>

<style scoped>
.shop-container {
  position: relative;
  min-height: 100vh;
  width: 100%;
  background: #f3f4f6;
  color: #1f2937;
  overflow-x: hidden;
}

.content-wrapper {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 40px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  font-size: 24px;
  font-weight: bold;
  background: linear-gradient(to right, #10b981, #059669);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  cursor: pointer;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.cart-icon-wrapper {
  cursor: pointer;
}

.header-cart-btn {
  font-size: 20px;
  border-color: #10b981;
  color: #10b981;
}

.header-cart-btn:hover {
  background: #10b9811a;
}

.main-content {
  flex: 1;
  padding: 40px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.hero-section {
  text-align: center;
  margin-bottom: 60px;
  animation: fadeInDown 1s ease-out;
}

.page-title {
  font-size: 48px;
  margin-bottom: 16px;
  background: linear-gradient(to right, #111827, #374151);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 4px;
}

.subtitle {
  font-size: 18px;
  color: #6b7280;
  letter-spacing: 2px;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
  margin-bottom: 40px;
  animation: fadeInDown 1s ease-out 0.1s backwards;
}

.filter-group {
  display: flex;
  align-items: center;
  background: white;
  padding: 6px 12px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.filter-label {
  font-size: 14px;
  color: #4b5563;
  margin-right: 10px;
  font-weight: 500;
}

.filter-select {
  width: 130px;
}

.filter-select :deep(.el-input__wrapper) {
  box-shadow: none !important;
  background-color: #f9fafb;
  border-radius: 6px;
}

.empty-state {
  margin-top: 60px;
  animation: fadeInDown 1s ease-out 0.2s backwards;
}

.category-section {
  margin-bottom: 50px;
  animation: fadeInUp 1s ease-out 0.2s backwards;
}

.category-title {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 2px solid #10b981;
  display: inline-block;
}

.view-more-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.view-more-btn {
  padding: 10px 24px;
}

.products-grid {
  /* removed animation to let category block handle it */
}

.product-card {
  background: #ffffff;
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 30px;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  border: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.product-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  border-color: rgba(16, 185, 129, 0.3);
}

.product-image {
  position: relative;
  height: 200px;
  overflow: hidden;
}

.product-img-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.real-product-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.product-card:hover .real-product-img {
  transform: scale(1.1);
}

.overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.product-card:hover .overlay {
  opacity: 1;
}

.sku-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(16, 185, 129, 0.9);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  z-index: 2;
}

.product-info {
  padding: 20px;
  text-align: left; /* changed from center to left for better sku/cart layout */
}

.product-name {
  font-size: 18px;
  margin-bottom: 8px;
  color: #111827;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tags-container {
  position: absolute;
  top: 10px;
  left: 10px;
  display: flex;
  gap: 6px;
  z-index: 2;
  flex-wrap: wrap;
}

.product-tag {
  border: none;
  font-weight: 500;
  border-radius: 4px;
}

.color-preview {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.color-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
  border: 1px solid rgba(0,0,0,0.1);
}

.color-name {
  font-size: 13px;
  color: #4b5563;
}

.product-desc {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 16px;
  height: 20px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price-action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #f3f4f6;
  padding-top: 12px;
}

.product-price {
  font-size: 20px;
  color: #10b981;
  font-weight: bold;
}

.sku-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Cart Drawer Styles */
.cart-content {
  padding: 10px;
}

.empty-cart {
  padding-top: 50px;
}

.cart-items {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.cart-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: #f9fafb;
  border-radius: 12px;
  border: 1px solid #f3f4f6;
}

.cart-item-img {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  object-fit: cover;
}

.cart-item-info {
  flex: 1;
}

.cart-item-name {
  font-weight: 600;
  font-size: 14px;
  color: #111827;
  margin-bottom: 4px;
}

.cart-item-sku {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.cart-item-price {
  font-weight: bold;
  color: #10b981;
  font-size: 14px;
}

.cart-footer {
  padding: 20px;
  border-top: 1px solid #f3f4f6;
}

.total-price {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: bold;
}

.price-value {
  color: #10b981;
  font-size: 24px;
}

.checkout-btn {
  width: 100%;
  height: 50px;
  background: #10b981;
  border: none;
  font-size: 16px;
  font-weight: bold;
}

.checkout-btn:hover {
  background: #059669;
}
</style>
