<template>
  <div class="login-page">
    <!-- Background Bubbles -->
    <div class="bubbles-container" ref="bubblesContainer"></div>

    <!-- Main Content Area -->
    <main class="hero-section" :class="{ 'shifted': isLoginOpen }">
      <header class="logo-area">
        <div class="logo">
          <img src="../assets/login/logo.png" alt="Logo" class="logo-img">
          智颜方正
        </div>
      </header>

      <div class="content-wrapper">
        <h1 class="hero-title">光影随心 <br> 重塑 <span class="highlight">非凡真我</span></h1>
        <p class="hero-subtitle">智能矫正与专属风格男妆，一键开启影像新视界。</p>
      </div>

      <!-- Dynamic Image Gallery -->
      <div class="image-gallery">
        <div class="carousel-stage">
          <div class="carousel-container">
            <div class="carousel-item" style="--i:0;">
              <img src="../assets/login/model1.png" alt="Model 1">
            </div>
            <div class="carousel-item" style="--i:1;">
              <img src="../assets/login/model2.png" alt="Model 2">
            </div>
            <div class="carousel-item" style="--i:2;">
              <img src="../assets/login/model3.png" alt="Model 3">
            </div>
            <div class="carousel-item" style="--i:3;">
              <img src="../assets/login/model4.png" alt="Model 4">
            </div>
            <div class="carousel-item" style="--i:4;">
              <img src="../assets/login/model5.png" alt="Model 5">
            </div>
            <div class="carousel-item" style="--i:5;">
              <img src="../assets/login/model6.png" alt="Model 6">
            </div>
            <div class="carousel-item" style="--i:6;">
              <img src="../assets/login/model1.png" alt="Model 7">
            </div>
            <div class="carousel-item" style="--i:7;">
              <img src="../assets/login/model2.png" alt="Model 8">
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Interactive Trigger (The Finger) -->
    <div class="interaction-trigger" :class="{ 'hidden': isLoginOpen }" @click="toggleLogin">
      <div class="finger-icon">
        <!-- Pointing Hand Icon -->
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M7 11L12 6M7 11L12 16M7 11H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <span class="trigger-text">探索一下</span>
    </div>

    <!-- Hidden Login/Register Container -->
    <div class="login-overlay" :class="{ 'active': isLoginOpen }" @click.self="toggleLogin">
      <div class="auth-panel">
        <button class="close-btn" @click="toggleLogin">&times;</button>
        
        <div class="auth-header">
          <h2>{{ isLoginMode ? '欢迎回来，探索智颜' : '开启智颜之旅' }}</h2>
          <p>{{ isLoginMode ? '登录以继续您的专属形象塑造' : '加入我们，体验前沿的男妆生成系统' }}</p>
        </div>
        
        <!-- Login Form -->
        <el-form
          v-if="isLoginMode"
          ref="loginFormRef"
          :model="loginForm"
          :rules="rules"
          class="auth-form"
          size="large"
          @submit.prevent
        >
          <el-form-item prop="phone">
            <el-input 
              v-model="loginForm.phone" 
              placeholder="请输入手机号" 
              class="custom-input"
            >
              <template #prefix>
                <el-icon><Iphone /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input 
              v-model="loginForm.password" 
              type="password" 
              placeholder="请输入密码" 
              show-password
              class="custom-input"
              @keyup.enter="handleLogin(loginFormRef)"
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <div class="form-actions-row">
             <a href="#" class="text-link">忘记密码？</a>
          </div>

          <el-button 
            type="primary" 
            class="submit-btn gradient-btn" 
            :loading="loading"
            @click="handleLogin(loginFormRef)"
          >
            立即登录
          </el-button>
        </el-form>

        <!-- Register Form -->
        <el-form
          v-else
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          class="auth-form"
          size="large"
          @submit.prevent
        >
          <el-form-item prop="phone">
            <el-input 
              v-model="registerForm.phone" 
              placeholder="请输入手机号" 
              class="custom-input"
            >
              <template #prefix>
                <el-icon><Iphone /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <el-input 
              v-model="registerForm.password" 
              type="password" 
              placeholder="请设置密码" 
              show-password
              class="custom-input"
              @input="checkPasswordStrength"
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
            <!-- Password Strength Indicator -->
            <div class="password-strength" v-if="registerForm.password">
              <div class="strength-bar" :class="{ 'active': pwdStrength >= 1, 'weak': pwdStrength === 1 }"></div>
              <div class="strength-bar" :class="{ 'active': pwdStrength >= 2, 'medium': pwdStrength === 2 }"></div>
              <div class="strength-bar" :class="{ 'active': pwdStrength >= 3, 'strong': pwdStrength === 3 }"></div>
            </div>
          </el-form-item>

          <el-form-item prop="code">
            <div class="code-input-group">
              <el-input 
                v-model="registerForm.code" 
                placeholder="请输入验证码" 
                class="custom-input code-input"
              >
                <template #prefix>
                  <el-icon><Key /></el-icon>
                </template>
              </el-input>
              <el-button 
                class="get-code-btn" 
                :disabled="isCountingDown" 
                @click="startCountdown"
              >
                {{ isCountingDown ? `${countdown}s 后重新获取` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>

          <el-form-item prop="agreement" class="agreement-item">
            <el-checkbox v-model="registerForm.agreement">
              我已阅读并同意 <a href="#" class="protocol-link">《用户协议》</a> 和 <a href="#" class="protocol-link">《隐私政策》</a>
            </el-checkbox>
          </el-form-item>

          <el-button 
            type="primary" 
            class="submit-btn gradient-btn" 
            :loading="loading"
            @click="handleRegister(registerFormRef)"
          >
            立即注册
          </el-button>
        </el-form>

        <div class="form-footer">
          <p v-if="isLoginMode">还没有账号? <a href="#" @click.prevent="toggleAuthMode">立即注册</a></p>
          <p v-else>已有账号? <a href="#" @click.prevent="toggleAuthMode">返回登录</a></p>
        </div>

        <!-- Social Login -->
        <div class="social-login-divider">
           <span>或通过以下方式</span>
        </div>
        <div class="social-icons">
           <button class="social-btn wechat-btn">
              <svg viewBox="0 0 1024 1024" width="24" height="24" xmlns="http://www.w3.org/2000/svg"><path d="M685.034 382.203c-13.886 0-27.18 1.4-39.814 3.905-24.576-88.74-118.966-155.132-232.193-155.132-132.85 0-241.134 94.624-241.134 212.008 0 66.822 34.693 125.865 89.262 165.263l-24.623 74.394 88.665-44.597c27.16 8.163 56.41 12.637 86.685 12.637 11.234 0 22.21-0.849 33.004-2.316C437.1 536.637 548.88 447.11 685.034 447.11z" fill="#07C160"/><path d="M685.034 447.11c-106.1 0-192.41 72.175-192.41 161.642 0 89.472 86.305 161.64 192.41 161.64 25.122 0 49.38-4.322 71.956-11.895l73.91 37.085-20.75-61.944c45.422-32.964 74.37-82.573 74.37-138.35v0.01C884.52 505.748 798.22 447.11 685.034 447.11z" fill="#07C160"/></svg>
           </button>
           <button class="social-btn google-btn">
              <svg viewBox="0 0 24 24" width="24" height="24" xmlns="http://www.w3.org/2000/svg"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
           </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Lock, Iphone, Key } from '@element-plus/icons-vue' // Add icon imports

const router = useRouter()
const userStore = useUserStore()
const loginFormRef = ref<FormInstance>()
const registerFormRef = ref<FormInstance>()
const bubblesContainer = ref<HTMLElement | null>(null)

const loading = ref(false)
const isLoginOpen = ref(false)
const isLoginMode = ref(true) // Toggle between Login and Register
let bubbleInterval: number | null = null

// --- State and Handlers for Verification Code ---
const isCountingDown = ref(false)
const countdown = ref(60)
let timer: number | null = null

const startCountdown = () => {
  if (isCountingDown.value) return
  isCountingDown.value = true
  countdown.value = 60
  ElMessage.success('验证码已发送至 138****0000 (演示)')
  timer = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer!)
      isCountingDown.value = false
    }
  }, 1000)
}

// --- Forms and Rules ---
const loginForm = reactive({
  phone: '',
  password: ''
})

const registerForm = reactive({
  phone: '',
  password: '',
  code: '',
  agreement: false
})

const pwdStrength = ref(0) // 0-3 scale
const checkPasswordStrength = (val: string) => {
  if (!val) { pwdStrength.value = 0; return }
  let strength = 0
  if (val.length >= 6) strength += 1
  if (/[a-zA-Z]/.test(val) && /[0-9]/.test(val)) strength += 1
  if (val.length >= 10 && /[^a-zA-Z0-9]/.test(val)) strength += 1
  pwdStrength.value = strength
}

const validateAgreement = (_rule: any, value: any, callback: any) => {
  if (!value) {
    callback(new Error('您必须同意用户协议与隐私政策'))
  } else {
    callback()
  }
}

const rules = reactive<FormRules>({
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ]
})

const registerRules = reactive<FormRules>({
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请设置密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' }
  ],
  agreement: [
    { validator: validateAgreement, trigger: 'change' }
  ]
})

const toggleLogin = () => {
  isLoginOpen.value = !isLoginOpen.value
}

const toggleAuthMode = () => {
  isLoginMode.value = !isLoginMode.value
  // Reset forms on toggle
  if (loginFormRef.value) loginFormRef.value.resetFields()
  if (registerFormRef.value) registerFormRef.value.resetFields()
}

const handleLogin = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  
  await formEl.validate((valid) => {
    if (valid) {
      loading.value = true
      // Simulate API call
      setTimeout(() => {
        loading.value = false
        // Allow demo login
        if (loginForm.phone === '13800138000' && loginForm.password === '123456') {
          const token = 'mock-token-' + Date.now()
          userStore.setToken(token)
          userStore.username = loginForm.phone
          ElMessage.success('登录成功')
          router.push('/')
        } else {
          ElMessage.error('手机号或密码错误 (演示号: 13800138000 / 123456)')
        }
      }, 1000)
    }
  })
}

const handleRegister = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  
  await formEl.validate((valid) => {
    if (valid) {
      loading.value = true
      // Simulate API call
      setTimeout(() => {
        loading.value = false
        ElMessage.success('注册成功，请重新登录')
        toggleAuthMode()
      }, 1500)
    }
  })
}

// Bubble Animation Logic
const createBubble = () => {
  if (!bubblesContainer.value) return

  const bubble = document.createElement('div')
  bubble.classList.add('bubble')

  // Random size
  const size = Math.random() * 60 + 20 // 20px - 80px
  bubble.style.width = `${size}px`
  bubble.style.height = `${size}px`
  bubble.style.left = `${Math.random() * 100}%`

  // Random animation duration
  const duration = Math.random() * 10 + 15 // 15s - 25s
  bubble.style.animationDuration = `${duration}s`

  // Random delay
  const delay = Math.random() * 5
  bubble.style.animationDelay = `${delay}s`

  bubblesContainer.value.appendChild(bubble)

  // Cleanup
  setTimeout(() => {
    bubble.remove()
  }, (duration + delay) * 1000)
}

onMounted(() => {
  // Initial batch
  for (let i = 0; i < 7; i++) {
    createBubble()
    const bubble = bubblesContainer.value?.lastChild as HTMLElement
    if (bubble) {
      const duration = parseFloat(bubble.style.animationDuration)
      const randomOffset = Math.random() * duration
      bubble.style.animationDelay = `-${randomOffset}s`
    }
  }
  
  // Interval
  bubbleInterval = window.setInterval(createBubble, 2000)
})

onUnmounted(() => {
  if (bubbleInterval) clearInterval(bubbleInterval)
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');

.login-page {
  /* CSS Variables */
  --primary-green: #2E7D32;
  --light-green: #E8F5E9;
  --accent-green: #66BB6A;
  --white: #ffffff;
  --dark-text: #1a1a1a;
  --muted-text: #666666;
  --glass-bg: rgba(255, 255, 255, 0.9);
  --glass-border: rgba(255, 255, 255, 0.5);
  --shadow-soft: 0 10px 30px rgba(46, 125, 50, 0.1);
  --glass-white: rgba(255, 255, 255, 0.85);
  --text-main: #1e293b;
  --text-muted: #64748b;

  font-family: 'Outfit', sans-serif;
  background-color: #ffffff;
  color: #1a1a1a;
  overflow: hidden;
  height: 100vh;
  width: 100vw;
  position: relative;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* Bubbles Container */
.bubbles-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

/* Deep selector for dynamically created elements in scoped css (or use :global(.bubble)) */
:deep(.bubble) {
  position: absolute;
  bottom: -100px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05) 60%, rgba(255, 255, 255, 0.1) 100%);
  box-shadow:
    inset 0 0 10px rgba(255, 255, 255, 0.4),
    0 0 10px rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  animation: floatUp linear infinite, wobble 3s ease-in-out infinite;
  opacity: 0;
}

:deep(.bubble::after) {
  content: '';
  position: absolute;
  top: 15%;
  left: 15%;
  width: 25%;
  height: 15%;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.8);
  filter: blur(1px);
  transform: rotate(-45deg);
}

@keyframes floatUp {
  0% {
    transform: translateY(0);
    opacity: 0;
  }
  10% {
    opacity: 0.8;
  }
  90% {
    opacity: 0.8;
  }
  100% {
    transform: translateY(-120vh);
    opacity: 0;
  }
}

@keyframes wobble {
  0%, 100% { margin-left: 0px; }
  50% { margin-left: 15px; }
}

/* Hero Section */
.hero-section {
  padding: 2rem 4rem;
  height: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  position: relative;
  z-index: 1;
  transition: transform 0.6s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.6s;
}

.hero-section.shifted {
  transform: translateX(-100px) scale(0.95);
  opacity: 0.5;
}

.content-wrapper {
  flex: 1;
  max-width: 50%;
  z-index: 2;
}

.hero-title {
  font-size: 5rem;
  line-height: 1.1;
  font-weight: 300;
  color: #1a1a1a;
  margin-bottom: 1.5rem;
}

.hero-title .highlight {
  font-weight: 700;
  color: #2E7D32;
  position: relative;
  display: inline-block;
}

.hero-title .highlight::after {
  content: '';
  position: absolute;
  bottom: 5px;
  left: 0;
  width: 100%;
  height: 15px;
  background-color: rgba(102, 187, 106, 0.2);
  z-index: -1;
  transform: rotate(-2deg);
}

.hero-subtitle {
  font-size: 1.2rem;
  color: #666666;
  max-width: none;
  white-space: nowrap;
}

/* 3D Carousel */
.image-gallery {
  flex: 1;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.carousel-stage {
  perspective: 1000px;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: translateX(-160px);
}

.carousel-container {
  position: relative;
  width: 220px;
  height: 300px;
  transform-style: preserve-3d;
  animation: spin 20s infinite linear;
}

.carousel-container:hover {
  animation-play-state: paused;
}

.carousel-item {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 15px;
  overflow: hidden;
  transform: rotateY(calc(var(--i) * 45deg)) translateZ(320px);
  border: 3px solid #ffffff;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
  -webkit-box-reflect: below 10px linear-gradient(transparent, transparent 60%, rgba(255, 255, 255, 0.4));
  backface-visibility: hidden;
  background-color: #ffffff;
}

.carousel-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

@keyframes spin {
  from { transform: rotateY(0deg); }
  to { transform: rotateY(360deg); }
}

/* Logo */
.logo {
  font-weight: 700;
  font-size: 1.5rem;
  color: #2E7D32;
  position: absolute;
  top: 2rem;
  left: 4rem;
  display: flex;
  align-items: center;
}

.logo-img {
  height: 80px;
  margin-right: 10px;
}

/* Interaction Trigger */
.interaction-trigger {
  position: absolute;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  cursor: pointer;
  z-index: 10;
  transition: transform 0.3s ease, opacity 0.3s;
}

.interaction-trigger:hover {
  transform: translateY(-50%) translateX(-10px);
}

.interaction-trigger.hidden {
  opacity: 0;
  pointer-events: none;
}

.finger-icon {
  width: 80px;
  height: 80px;
  background: #2E7D32;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 5px 20px rgba(46, 125, 50, 0.3);
  animation: bounceRight 2s infinite;
}

.finger-icon svg {
  width: 40px;
  height: 40px;
  transform: rotate(180deg);
}

@keyframes bounceRight {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(10px); }
}

.trigger-text {
  font-size: 1.2rem;
  font-weight: 500;
  color: #2E7D32;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  letter-spacing: 4px;
}

/* Login Overlay - Panel Modification ONLY */
.login-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(8px);
  z-index: 20;
  opacity: 0;
  visibility: hidden;
  transition: all 0.5s ease;
  display: flex;
  justify-content: flex-end;
}

.login-overlay.active {
  opacity: 1;
  visibility: visible;
}

.auth-panel {
  width: 500px;
  height: 100%;
  background: var(--glass-white);
  border-left: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: -20px 0 50px rgba(0, 0, 0, 0.05);
  padding: 5rem 5rem 4rem 5rem;
  transform: translateX(100%);
  transition: transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 21;
  overflow-y: auto; /* 允许在内容过多时滚动，防止被截断 */
}

.login-overlay.active .auth-panel {
  transform: translateX(0);
}

.close-btn {
  position: absolute;
  top: 2rem;
  right: 2rem;
  background: none;
  border: none;
  font-size: 2rem;
  cursor: pointer;
  color: var(--text-muted);
  transition: color 0.3s;
}

.close-btn:hover {
  color: var(--primary-green);
}

.auth-header {
  margin-bottom: 3rem;
}

.auth-header h2 {
  font-size: 2rem;
  font-weight: 700;
  color: var(--primary-green);
  margin-bottom: 0.75rem;
}

.auth-header p {
  color: var(--text-muted);
  font-size: 1rem;
}

/* Auth Forms Styling */
.custom-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.5) !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02) !important;
  border-radius: 12px;
  padding: 8px 15px;
  transition: all 0.3s;
}

.custom-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--primary-green) !important;
}

.form-actions-row {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 2rem;
}

.text-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}

.text-link:hover {
  color: var(--primary-green);
}

.submit-btn {
  width: 100%;
  height: 56px;
  border-radius: 14px;
  font-size: 1.1rem;
  font-weight: 600;
  border: none;
  margin-top: 1rem;
  cursor: pointer;
}

.gradient-btn {
  background: var(--primary-green) !important;
  color: white !important;
  box-shadow: 0 10px 20px rgba(46, 125, 50, 0.2);
}

/* Registration Specifics */
.code-input-group {
  display: flex;
  gap: 1rem;
}

.code-input {
  flex: 1;
}

.get-code-btn {
  height: 52px;
  border-radius: 12px;
  padding: 0 1.5rem;
  font-size: 0.9rem;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #e2e8f0;
  color: var(--text-main);
  cursor: pointer;
}

.get-code-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.password-strength {
  display: flex;
  gap: 4px;
  margin-top: 8px;
}

.strength-bar {
  flex: 1;
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  transition: all 0.3s;
}

.strength-bar.active.weak { background: #ff4d4f; }
.strength-bar.active.medium { background: #faad14; }
.strength-bar.active.strong { background: #52c41a; }

.agreement-item {
  margin-top: 1rem;
}

:deep(.el-checkbox__label) {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.protocol-link {
  color: var(--primary-green);
  text-decoration: none;
}

.form-footer {
  margin-top: 2rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.form-footer a {
  color: var(--primary-green);
  font-weight: 600;
  text-decoration: none;
}

/* Social Login Box */
.social-login-divider {
  margin: 3rem 0 2rem;
  display: flex;
  align-items: center;
  text-align: center;
  color: #cbd5e1;
}

.social-login-divider::before, .social-login-divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid #f1f5f9;
}

.social-login-divider span {
  padding: 0 15px;
  font-size: 0.85rem;
  color: #000000;
  font-weight: 500;
}

.social-icons {
  display: flex;
  justify-content: center;
  gap: 2rem;
}

.social-btn {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  border: 1px solid #f1f5f9;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
}

.social-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(0,0,0,0.05);
  border-color: #e2e8f0;
}
</style>
