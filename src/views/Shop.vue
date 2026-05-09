<template>
  <div class="shop-container">
    <ModernBackground />
    
    <div class="content-wrapper">
      <header class="header">
        <div class="logo-wrapper" @click="router.push('/')">
          <img src="../assets/brand/yanxuan-menx-logo.png" alt="颜选MenX" class="logo-img">
        </div>
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
            <span class="filter-label">分类</span>
            <el-select v-model="filterCategory" placeholder="全部" size="default" class="filter-select">
              <el-option label="全部" value="" />
              <el-option label="底妆" value="base" />
              <el-option label="眉部" value="brow" />
              <el-option label="眼部" value="eye" />
              <el-option label="唇部" value="lip" />
              <el-option label="修容" value="contour" />
            </el-select>
          </div>
          <div class="filter-group">
            <span class="filter-label">排序</span>
            <el-select v-model="sortBy" placeholder="默认" size="default" class="filter-select">
              <el-option label="默认" value="" />
              <el-option label="价格从低到高" value="price_asc" />
              <el-option label="价格从高到低" value="price_desc" />
              <el-option label="销量优先" value="sales" />
            </el-select>
          </div>
        </div>

        <div class="products-grid">
          <div 
            class="product-card" 
            v-for="product in products" 
            :key="product.product_id"
            @click="viewProduct(product)"
          >
            <div class="product-image-wrapper">
              <img :src="product.image_url || `https://neeko-copilot.bytedance.net/api/text_to_image?prompt=men%20cosmetics%20product%20${product.name}&image_size=square`" alt="商品图片" class="product-image">
              <div class="product-tags">
                <el-tag size="small" type="success" effect="dark" v-if="product.tags?.includes('PCA推荐')">PCA推荐</el-tag>
                <el-tag size="small" type="warning" effect="dark" v-if="product.tags?.includes('热门试用')">热门试用</el-tag>
                <el-tag size="small" type="info" effect="dark" v-if="product.tags?.includes('新手友好')">新手友好</el-tag>
              </div>
            </div>
            <div class="product-info">
              <div class="product-name">{{ product.name }}</div>
              <div class="product-brand">{{ product.brand }}</div>
              <div class="product-price">¥{{ product.price }}</div>
              <div class="product-colors" v-if="product.color_hex">
                <span class="color-label">色号:</span>
                <div class="color-dots">
                  <span class="color-dot" :style="{ backgroundColor: product.color_hex }" :title="product.shade_name"></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <el-drawer title="购物车" :visible="drawerVisible" @close="drawerVisible = false" direction="rtl" size="400px">
        <div class="cart-content">
          <div v-if="cart.length === 0" class="empty-cart">
            <el-icon :size="48" class="empty-icon"><ShoppingCart /></el-icon>
            <p>购物车是空的</p>
            <el-button type="primary" @click="router.push('/shop')">去购物</el-button>
          </div>
          <div v-else>
            <div class="cart-items">
              <div 
                class="cart-item" 
                v-for="item in cart" 
                :key="item.product_id"
              >
                <img :src="item.image" class="cart-item-image">
                <div class="cart-item-info">
                  <div class="cart-item-name">{{ item.name }}</div>
                  <div class="cart-item-price">¥{{ item.price }}</div>
                  <div class="cart-item-quantity">
                    <el-button size="small" @click="updateQuantity(item.product_id, item.quantity - 1)">-</el-button>
                    <span>{{ item.quantity }}</span>
                    <el-button size="small" @click="updateQuantity(item.product_id, item.quantity + 1)">+</el-button>
                  </div>
                </div>
                <el-button size="small" type="danger" @click="removeFromCart(item.product_id)">删除</el-button>
              </div>
            </div>
            <div class="cart-summary">
              <div class="summary-row">
                <span>商品数量</span>
                <span>{{ cartTotalQuantity }}</span>
              </div>
              <div class="summary-row total">
                <span>合计</span>
                <span>¥{{ cartTotalPrice }}</span>
              </div>
              <el-button type="primary" size="large" class="checkout-btn" @click="checkout">结算</el-button>
            </div>
          </div>
        </div>
      </el-drawer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ModernBackground from '../components/ModernBackground.vue'
import { ShoppingCart } from '@element-plus/icons-vue'
import { getProducts } from '../api/products'
import type { Product, CartItem } from '../api/products'

const router = useRouter()
const route = useRoute()

const filterSeason = ref('')
const filterCategory = ref('')
const sortBy = ref('')
const drawerVisible = ref(false)

const products = ref<Product[]>([])
const cart = ref<CartItem[]>([])

const cartTotalQuantity = computed(() => {
  return cart.value.reduce((sum, item) => sum + item.quantity, 0)
})

const cartTotalPrice = computed(() => {
  return cart.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
})

const loadProducts = async () => {
  const season = route.query.season as string || filterSeason.value
  const category = filterCategory.value
  
  const result = await getProducts(season, category, 50)
  if (result && result.products) {
    products.value = result.products
  }
}

const viewProduct = (product: Product) => {
  router.push({ name: 'ProductDetail', params: { id: product.product_id } })
}

const updateQuantity = (productId: number, quantity: number) => {
  if (quantity <= 0) {
    removeFromCart(productId)
    return
  }
  const item = cart.value.find(item => item.product_id === productId)
  if (item) {
    item.quantity = quantity
    localStorage.setItem('cart', JSON.stringify(cart.value))
  }
}

const removeFromCart = (productId: number) => {
  cart.value = cart.value.filter(item => item.product_id !== productId)
  localStorage.setItem('cart', JSON.stringify(cart.value))
}

const checkout = () => {
  alert('结算功能开发中')
}

onMounted(() => {
  loadProducts()
  
  const savedCart = localStorage.getItem('cart')
  if (savedCart) {
    cart.value = JSON.parse(savedCart)
  }
  
  if (route.query.season) {
    filterSeason.value = route.query.season as string
  }
})
</script>

<style scoped>
.shop-container {
  min-height: 100vh;
  position: relative;
}

.content-wrapper {
  position: relative;
  z-index: 1;
}

.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  padding: 16px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.05);
}

.logo-wrapper {
  cursor: pointer;
}

.logo-img {
  height: 40px;
  width: auto;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-btn {
  color: #64748b;
  font-weight: 500;
}

.cart-icon-wrapper {
  position: relative;
  cursor: pointer;
}

.cart-badge {
  position: absolute;
  top: -8px;
  right: -8px;
}

.header-cart-btn {
  font-size: 24px;
  color: #2E7D32;
}

.main-content {
  padding-top: 80px;
  padding-left: 40px;
  padding-right: 40px;
  padding-bottom: 60px;
}

.hero-section {
  text-align: center;
  margin-bottom: 40px;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.subtitle {
  color: #64748b;
  font-size: 16px;
}

.filter-bar {
  display: flex;
  gap: 32px;
  justify-content: center;
  margin-bottom: 40px;
  padding: 20px 30px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 15px rgba(0, 0, 0, 0.05);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

.filter-select {
  width: 140px;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.product-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 15px rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.product-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.1);
}

.product-image-wrapper {
  position: relative;
  height: 200px;
  overflow: hidden;
}

.product-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-tags {
  position: absolute;
  top: 10px;
  left: 10px;
  display: flex;
  gap: 6px;
}

.product-info {
  padding: 16px;
}

.product-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-brand {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.product-price {
  font-size: 16px;
  font-weight: 700;
  color: #E65100;
  margin-bottom: 8px;
}

.product-colors {
  display: flex;
  align-items: center;
  gap: 8px;
}

.color-label {
  font-size: 12px;
  color: #94a3b8;
}

.color-dots {
  display: flex;
  gap: 6px;
}

.color-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid #e2e8f0;
}

.cart-content {
  padding: 20px;
  height: calc(100vh - 120px);
  overflow-y: auto;
}

.empty-cart {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #94a3b8;
}

.empty-icon {
  margin-bottom: 16px;
}

.cart-items {
  margin-bottom: 24px;
}

.cart-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.cart-item-image {
  width: 80px;
  height: 80px;
  border-radius: 8px;
  object-fit: cover;
}

.cart-item-info {
  flex: 1;
}

.cart-item-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 4px;
}

.cart-item-price {
  font-size: 14px;
  font-weight: 600;
  color: #E65100;
  margin-bottom: 8px;
}

.cart-item-quantity {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cart-summary {
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.summary-row.total {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 16px;
}

.checkout-btn {
  width: 100%;
  border-radius: 8px;
}

@media (max-width: 1200px) {
  .products-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 900px) {
  .header {
    padding: 12px 20px;
  }
  
  .filter-bar {
    flex-wrap: wrap;
    gap: 16px;
  }
  
  .products-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
