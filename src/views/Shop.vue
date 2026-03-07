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
          <h1 class="page-title">绅士精选</h1>
          <p class="subtitle">专为男士打造的高端护肤与美妆系列</p>
        </div>

        <div class="products-grid">
          <el-row :gutter="30">
            <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="item in products" :key="item.id">
              <div class="product-card">
                <div class="product-image">
                  <div class="product-img-container">
                    <img :src="item.image" :alt="item.name" class="real-product-img" />
                  </div>
                  <div class="sku-badge">{{ item.sku }}</div>
                  <div class="overlay">
                    <el-button type="primary" plain round @click="handleTryOn(item)">立即试用</el-button>
                  </div>
                </div>
                <div class="product-info">
                  <h3 class="product-name">{{ item.name }}</h3>
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
            <el-empty description="购物车空空如也" />
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
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ShoppingCart, Delete } from '@element-plus/icons-vue'
import ModernBackground from '../components/ModernBackground.vue'

const router = useRouter()

const products = [
  { id: 1, sku: 'S1-CLN', name: '男士焕能洁面乳', desc: '深层清洁，控油保湿', price: '129', image: new URL('../assets/products/cleanser.jpg', import.meta.url).href },
  { id: 2, sku: 'S1-TNR', name: '清爽保湿爽肤水', desc: '收缩毛孔，醒肤补水', price: '159', image: new URL('../assets/products/toner.jpg', import.meta.url).href },
  { id: 3, sku: 'S1-CRM', name: '多效修护面霜', desc: '抗皱紧致，滋润不油腻', price: '299', image: new URL('../assets/products/cream.jpg', import.meta.url).href },
  { id: 4, sku: 'S2-BBC', name: '自然色男士BB霜', desc: '色号: 自然偏白，遮瑕修颜', price: '189', image: new URL('../assets/products/bb_cream.jpg', import.meta.url).href },
  { id: 5, sku: 'S2-SPY', name: '定型喷雾', desc: '持久定型，清爽自然', price: '89', image: new URL('../assets/products/spray.jpg', import.meta.url).href },
  { id: 6, sku: 'S2-BRW', name: '男士眉笔', desc: '色号: 深棕灰，立体塑形', price: '59', image: new URL('../assets/products/eyebrow_pencil.jpg', import.meta.url).href },
  { id: 7, sku: 'S3-AFT', name: '须后舒缓乳', desc: '舒缓修护，清凉止痛', price: '119', image: new URL('../assets/products/aftershave.jpg', import.meta.url).href },
  { id: 8, sku: 'S3-MSK', name: '男士专用面膜', desc: '深层补水，提亮肤色', price: '99', image: new URL('../assets/products/mask.jpg', import.meta.url).href },
]

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

.products-grid {
  animation: fadeInUp 1s ease-out 0.3s backwards;
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
