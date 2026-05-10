<template>
  <div class="home-container" @scroll="handleScroll">
    <ModernBackground />
    <FloatingImages />
    
    <div class="content-wrapper">
      <header class="header" :class="{ 'header-hidden': !headerVisible }">
        <div class="logo-wrapper" @click="router.push('/')">
          <img src="../assets/brand/yanxuan-menx-logo.png" alt="颜选MenX" class="logo-img">
        </div>
        <div class="header-right">
          <div class="nav-item" @click="router.push('/shop')">
            <el-icon class="nav-icon"><Goods /></el-icon>
            <span>绅士精选</span>
          </div>
          <div class="divider"></div>
          <div class="user-actions" v-if="userStore.token">
            <el-dropdown trigger="click">
              <span class="el-dropdown-link" style="cursor: pointer; display: flex; align-items: center;">
                <el-avatar :size="36" src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png" />
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="router.push('/profile')">个人中心</el-dropdown-item>
                  <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div class="user-actions" v-else>
            <el-button type="primary" @click="router.push('/login')">登录</el-button>
          </div>
        </div>
      </header>

      <main class="main-section">
        <div class="hero-content">
          <h1 class="main-title">智能矫正与专属风格男妆<br>一键开启影像新视界</h1>
          <p class="description">
            颜选MenX，为现代男士打造专属形象管理方案。<br>
            AI智能矫正光影角度，定制风格妆容，重塑你的魅力瞬间。
          </p>
          <div class="cta-buttons">
            <el-button class="cta-primary" size="large" @click="router.push('/upload')">
              <el-icon class="el-icon--left"><Camera /></el-icon>
              开始体验
            </el-button>
            <el-button class="cta-secondary" size="large" @click="router.push('/shop')">
              探索商品
            </el-button>
          </div>
        </div>
      </main>

      <section class="features-section">
        <h2 class="section-title">为什么选择我们</h2>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><Star /></el-icon>
            </div>
            <h3>AI智能分析</h3>
            <p>基于PCA季型分析，精准推荐最适合您的色系和产品</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><MagicStick /></el-icon>
            </div>
            <h3>虚拟试妆</h3>
            <p>实时预览妆容效果，降低试错成本，找到最适合的风格</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><ShoppingBag /></el-icon>
            </div>
            <h3>一键购买</h3>
            <p>试妆满意直接购买推荐产品，形成完整商业闭环</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><Collection /></el-icon>
            </div>
            <h3>方案保存</h3>
            <p>保存个人妆容方案，随时复用，打造专属风格</p>
          </div>
        </div>
      </section>

      <section class="styles-section">
        <h2 class="section-title">三种风格，一键切换</h2>
        <div class="styles-grid">
          <div class="style-card" @click="goToMakeup('natural')">
            <div class="style-image">
              <div class="style-overlay"></div>
              <img src="/images/styles/natural.png" alt="自然清透">
            </div>
            <div class="style-info">
              <h3>自然清透</h3>
              <p>日常通勤的最佳选择</p>
            </div>
          </div>
          <div class="style-card" @click="goToMakeup('business')">
            <div class="style-image">
              <div class="style-overlay"></div>
              <img src="/images/styles/business.png" alt="轻熟职场">
            </div>
            <div class="style-info">
              <h3>轻熟职场</h3>
              <p>展现专业自信形象</p>
            </div>
          </div>
          <div class="style-card" @click="goToMakeup('korean')">
            <div class="style-image">
              <div class="style-overlay"></div>
              <img src="/images/styles/idol.png" alt="韩系潮流">
            </div>
            <div class="style-info">
              <h3>韩系潮流</h3>
              <p>时尚精致的魅力风格</p>
            </div>
          </div>
        </div>
      </section>

      <footer class="footer">
        <div class="footer-content">
          <div class="footer-brand">
            <img src="../assets/brand/yanxuan-menx-logo.png" alt="颜选MenX" class="footer-logo">
            <p>为现代男士打造专属形象管理方案</p>
          </div>
          <div class="footer-links">
            <div class="link-group">
              <h4>产品服务</h4>
              <ul>
                <li><a href="#features">功能介绍</a></li>
                <li><a href="#styles">妆容风格</a></li>
                <li><a href="/shop">商品商城</a></li>
              </ul>
            </div>
            <div class="link-group">
              <h4>关于我们</h4>
              <ul>
                <li><a href="#about">品牌故事</a></li>
                <li><a href="#contact">联系我们</a></li>
                <li><a href="#privacy">隐私政策</a></li>
              </ul>
            </div>
          </div>
        </div>
        <div class="footer-bottom">
          <p>© 2025 颜选MenX Team. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import ModernBackground from '../components/ModernBackground.vue'
import FloatingImages from '../components/FloatingImages.vue'
import { Goods, Camera, Star, MagicStick, ShoppingBag, Collection } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()
const headerVisible = ref(true)
let lastScrollY = 0

const handleScroll = (event: any) => {
  const currentScrollY = event.target.scrollTop
  headerVisible.value = currentScrollY < lastScrollY || currentScrollY < 50
  lastScrollY = currentScrollY
}

const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}

const goToMakeup = (style: string) => {
  router.push({ name: 'Result', query: { style } })
}

onMounted(() => {})

onUnmounted(() => {})
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
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
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.header-hidden {
  transform: translateY(-100%);
}

.logo-wrapper {
  cursor: pointer;
}

.logo-img {
  height: 40px;
  width: auto;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #333;
  font-weight: 500;
  padding: 8px 16px;
  border-radius: 20px;
  transition: all 0.3s ease;
}

.nav-item:hover {
  background: rgba(46, 125, 50, 0.1);
  color: #2E7D32;
}

.nav-icon {
  font-size: 18px;
}

.divider {
  width: 1px;
  height: 24px;
  background: #e2e8f0;
}

.user-actions {
  display: flex;
  align-items: center;
}

.main-section {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 120px 40px 80px;
}

.hero-content {
  text-align: center;
  max-width: 800px;
}

.main-title {
  font-size: 48px;
  font-weight: 800;
  color: #1a1a1a;
  line-height: 1.3;
  margin-bottom: 24px;
}

.description {
  font-size: 18px;
  color: #64748b;
  line-height: 1.8;
  margin-bottom: 40px;
}

.cta-buttons {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.cta-primary {
  background: linear-gradient(135deg, #2E7D32, #1B5E20) !important;
  border: none !important;
  padding: 14px 40px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  border-radius: 50px !important;
  box-shadow: 0 10px 30px rgba(46, 125, 50, 0.3);
  color: white !important;
}

.cta-secondary {
  background: white !important;
  color: #2E7D32 !important;
  border: 2px solid #2E7D32 !important;
  padding: 14px 40px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  border-radius: 50px !important;
}

.features-section {
  padding: 80px 40px;
  background: white;
}

.section-title {
  text-align: center;
  font-size: 32px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 48px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 32px;
  max-width: 1200px;
  margin: 0 auto;
}

.feature-card {
  background: white;
  padding: 32px;
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  text-align: center;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #E8F5E9, #C8E6C9);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: #2E7D32;
}

.feature-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 12px;
}

.feature-card p {
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
}

.styles-section {
  padding: 80px 40px;
  background: #f8fafc;
}

.styles-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.style-card {
  background: white;
  border-radius: 20px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.style-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.1);
}

.style-image {
  position: relative;
  height: 280px;
  overflow: hidden;
}

.style-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.style-card:hover .style-image img {
  transform: scale(1.1);
}

.style-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.6));
}

.style-info {
  padding: 20px;
}

.style-info h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 4px;
}

.style-info p {
  font-size: 14px;
  color: #64748b;
}

.footer {
  background: #1a1a1a;
  color: white;
  padding: 60px 40px 30px;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
}

.footer-brand {
  flex: 1;
}

.footer-logo {
  height: 50px;
  width: auto;
  margin-bottom: 12px;
}

.footer-brand p {
  color: #94a3b8;
  font-size: 14px;
}

.footer-links {
  display: flex;
  gap: 60px;
}

.link-group h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #cbd5e1;
}

.link-group ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.link-group li {
  margin-bottom: 8px;
}

.link-group a {
  color: #94a3b8;
  font-size: 14px;
  text-decoration: none;
  transition: color 0.3s ease;
}

.link-group a:hover {
  color: white;
}

.footer-bottom {
  max-width: 1200px;
  margin: 0 auto;
  padding-top: 30px;
  border-top: 1px solid #334155;
  text-align: center;
}

.footer-bottom p {
  color: #64748b;
  font-size: 14px;
}

@media (max-width: 900px) {
  .header {
    padding: 12px 20px;
  }
  
  .main-title {
    font-size: 32px;
  }
  
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .styles-grid {
    grid-template-columns: 1fr;
  }
  
  .footer-content {
    flex-direction: column;
    gap: 40px;
  }
}
</style>
