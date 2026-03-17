<template>
  <div class="home-container" @scroll="handleScroll">
    <ModernBackground />
    <FloatingImages />
    
    <div class="content-wrapper">
      <header class="header" :class="{ 'header-hidden': !headerVisible }">
        <div class="logo">智颜方正</div>
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

      <main class="main-content">
        <!-- Hero Section -->
        <section class="hero-section">
          <h1 class="main-title">智能图像矫正<br>与风格男妆生成系统</h1>
          <p class="description">
            基于先进的深度学习算法，为您提供专业级的人像矫正与风格化美妆服务。<br>
            一键上传，智能优化，展现最自信的自己。
          </p>
          
          <div class="action-area">
            <el-button 
              type="primary" 
              size="large" 
              class="start-btn"
              @click="handleStart"
            >
              立即体验
              <el-icon class="el-icon--right"><ArrowRight /></el-icon>
            </el-button>
          </div>

          <div class="scroll-indicator" @click="scrollToShowcase">
            <span>探索更多风格</span>
            <el-icon class="scroll-icon"><ArrowDown /></el-icon>
          </div>
        </section>

        <!-- Showcase Section -->
        <section class="showcase-section" id="showcase" v-if="showShowcase">
          <h2 class="section-title">探索多面魅力</h2>
          <p class="section-subtitle">为您量身定制的多种风格选择</p>
          
          <div class="style-grid">
            <div class="style-card" v-for="(style, index) in styles" :key="index">
              <div class="card-image">
                <img :src="style.image" :alt="style.title" />
                <div class="card-overlay">
                  <el-button round class="try-btn" @click="handleStart(style)">尝试此风格</el-button>
                </div>
              </div>
              <div class="card-content">
                <h3>{{ style.title }}</h3>
                <p>{{ style.desc }}</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer class="footer" v-if="showShowcase">
        <p>© 2025 智颜方正 Team. All Rights Reserved.</p>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import FloatingImages from '../components/FloatingImages.vue'
import ModernBackground from '../components/ModernBackground.vue'
import { ArrowRight, Goods, ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const showShowcase = ref(false)
const headerVisible = ref(true)
const lastScrollTop = ref(0)

const styles = [
  {
    title: '自然清透',
    desc: '还原肌肤本真质感，打造伪素颜的清爽形象',
    image: '/images/styles/natural.png'
  },
  {
    title: '韩系潮流',
    desc: '紧跟时尚潮流，打造精致亮眼的舞台级妆效',
    image: '/images/styles/idol.png'
  },
  {
    title: '轻熟职场',
    desc: '干练利落的职场形象，提升专业度与信赖感',
    image: '/images/styles/business.png'
  },
  {
    title: '硬朗质感',
    desc: '强调面部轮廓与线条，展现成熟稳重的男性魅力',
    image: '/images/styles/textured.png'
  }
]

const handleStart = (style?: any) => {
  if (style && style.title === '硬朗质感') {
    ElMessage.warning('该风格正在开发中，敬请期待')
    return
  }

  if (userStore.token) {
    router.push('/upload')
  } else {
    ElMessage.warning('请先登录以使用功能')
    router.push('/login')
  }
}

const handleLogout = () => {
  userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

const scrollToShowcase = async () => {
  showShowcase.value = true
  await nextTick()
  document.getElementById('showcase')?.scrollIntoView({ behavior: 'smooth' })
}

const handleScroll = (e: Event) => {
  const target = e.target as HTMLElement
  const scrollTop = target.scrollTop
  
  if (scrollTop > lastScrollTop.value && scrollTop > 50) {
    // Scrolling down & past top
    headerVisible.value = false
  } else {
    // Scrolling up
    headerVisible.value = true
  }
  
  lastScrollTop.value = scrollTop
}
</script>

<style scoped>
.home-container {
  position: relative;
  height: 100vh;
  width: 100%;
  background: #f8fafc;
  overflow-y: auto; /* Enable vertical scrolling */
  overflow-x: hidden;
  color: #1f2937;
  scroll-behavior: smooth;
}

.content-wrapper {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 100;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 40px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0,0,0,0.05);
  transition: transform 0.3s ease;
}

.header-hidden {
  transform: translateY(-100%);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(16, 185, 129, 0.2);
  color: #1f2937;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.nav-item:hover {
  background: #fff;
  border-color: #10b981;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.divider {
  width: 1px;
  height: 24px;
  background: rgba(0, 0, 0, 0.1);
  margin: 0 10px;
}

.logo {
  font-size: 24px;
  font-weight: bold;
  background: linear-gradient(to right, #10b981, #059669);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.username {
  margin-right: 15px;
  color: #4b5563;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-top: 80px; /* Header height */
}

/* Hero Section */
.hero-section {
  min-height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 0 20px;
  position: relative;
}

.main-title {
  font-size: 64px;
  line-height: 1.2;
  margin-bottom: 24px;
  font-weight: 800;
  letter-spacing: 2px;
  color: #111827;
  background: linear-gradient(135deg, #111827 0%, #374151 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.description {
  font-size: 18px;
  line-height: 1.6;
  color: #4b5563;
  margin-bottom: 48px;
  max-width: 600px;
}

.start-btn {
  padding: 25px 50px;
  font-size: 20px;
  border-radius: 50px;
  background: linear-gradient(90deg, #10b981 0%, #059669 100%);
  border: none;
  transition: all 0.3s ease;
  box-shadow: 0 10px 30px rgba(16, 185, 129, 0.3);
}

.start-btn:hover {
  transform: translateY(-3px) scale(1.02);
  box-shadow: 0 20px 40px rgba(16, 185, 129, 0.4);
}

.scroll-indicator {
  position: absolute;
  bottom: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #9ca3af;
  cursor: pointer;
  transition: color 0.3s;
  animation: bounce 2s infinite;
}

.scroll-indicator:hover {
  color: #10b981;
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-10px); }
  60% { transform: translateY(-5px); }
}

/* Showcase Section */
.showcase-section {
  min-height: 100vh;
  padding: 100px 40px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(20px);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.section-title {
  font-size: 42px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 16px;
}

.section-subtitle {
  font-size: 18px;
  color: #6b7280;
  margin-bottom: 60px;
}

.style-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 40px;
  width: 100%;
  max-width: 1400px;
}

.style-card {
  background: #fff;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
  transition: all 0.4s ease;
  cursor: pointer;
}

.style-card:hover {
  transform: translateY(-15px);
  box-shadow: 0 25px 50px rgba(0,0,0,0.1);
}

.card-image {
  width: 100%;
  height: 350px;
  overflow: hidden;
  position: relative;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.6s ease;
}

.style-card:hover .card-image img {
  transform: scale(1.1);
}

.card-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.3);
  display: flex;
  justify-content: center;
  align-items: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.style-card:hover .card-overlay {
  opacity: 1;
}

.try-btn {
  background: #fff;
  color: #1f2937;
  border: none;
  padding: 12px 30px;
  font-weight: 600;
  transform: translateY(20px);
  transition: transform 0.3s ease;
}

.style-card:hover .try-btn {
  transform: translateY(0);
}

.card-content {
  padding: 25px;
  text-align: center;
}

.card-content h3 {
  font-size: 22px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 10px;
}

.card-content p {
  color: #6b7280;
  font-size: 14px;
  line-height: 1.6;
}

.footer {
  padding: 40px 20px;
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
  background: #fff;
  border-top: 1px solid #f3f4f6;
}
</style>
