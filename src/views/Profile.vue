<template>
  <div class="profile-container">
    <div class="profile-header">
      <div class="user-info">
        <el-upload
          class="avatar-uploader"
          :show-file-list="false"
          :http-request="handleAvatarUpload"
          accept="image/*"
        >
          <el-avatar :size="80" :src="userInfo.avatar || 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'" class="user-avatar" />
          <div class="avatar-hover-mask">
            <el-icon><Camera /></el-icon>
          </div>
        </el-upload>
        <div class="user-details">
          <div class="user-name-wrapper">
            <h2 v-if="!isEditingNickname" class="user-name">{{ userInfo.nickname || '智颜用户' }}</h2>
            <el-input 
              v-else 
              v-model="editNicknameValue" 
              size="small" 
              class="nickname-input"
              @blur="saveNickname"
              @keyup.enter="saveNickname"
              ref="nicknameInputRef"
            />
            <el-icon class="edit-icon" @click="startEditNickname"><Edit /></el-icon>
          </div>
          <div class="user-tags">
            <span class="season-tag" v-if="userInfo.season_type || (userInfo as any).season">
              <el-icon><MagicStick /></el-icon> {{ userInfo.season_type || (userInfo as any).season }}
            </span>
            <span class="season-tag placeholder" v-else>
              <el-icon><MagicStick /></el-icon> 暂无季型数据
            </span>
            <span class="phone-tag">
              <el-icon><Iphone /></el-icon> {{ userInfo.phone }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="profile-content">
      <!-- Row 1: Photos & Plans -->
      <div class="card-grid">
        <div class="profile-card photo-card">
          <div class="card-header">
            <h3>照片库</h3>
            <div class="header-actions">
              <el-button type="success" link @click="loadUserData">刷新数据</el-button>
              <el-button type="primary" link>查看全部</el-button>
            </div>
          </div>
          <p class="card-desc">管理您的每一次颜值升级</p>
          <div class="photo-list">
            <template v-if="userImages.length > 0">
              <div class="photo-item" v-for="img in userImages.slice(0, 5)" :key="img.image_id">
                <el-image :src="img.url" fit="cover" :preview-src-list="userImages.map(i => i.url)" />
                <div class="photo-label success" v-if="img.image_type === 'corrected'">已诊断</div>
                <div class="photo-label pending" v-else>原图</div>
              </div>
            </template>
            <div class="photo-item upload-item" @click="router.push('/upload')">
              <el-icon><Plus /></el-icon>
              <span>上传新图</span>
            </div>
          </div>
        </div>

        <div class="profile-card plan-card">
          <div class="card-header">
            <h3>我的个人形象方案库</h3>
            <el-button type="primary" link>管理方案</el-button>
          </div>
          <p class="card-desc">收藏的定制妆容与装扮</p>
          <div class="plan-list">
            <el-empty description="暂无保存的方案" :image-size="60" v-if="savedPlans.length === 0">
              <el-button type="primary" plain @click="router.push('/result')">去生成方案</el-button>
            </el-empty>
            <div v-else class="plan-grid">
              <div class="plan-item" v-for="plan in savedPlans" :key="plan.id">
                <div class="plan-cover">
                  <img :src="plan.cover" />
                  <span class="scene-tag-overlay">{{ plan.scene }}</span>
                </div>
                <div class="plan-info">
                  <h4>{{ plan.name }}</h4>
                  <p class="plan-reason">{{ plan.reason }}</p>
                  <p class="plan-meta">包含 {{ plan.itemCount || 3 }} 件精选单品</p>
                  <div class="plan-actions">
                    <el-button size="small" type="primary" plain @click="handleCart(plan)">一键购齐</el-button>
                    <el-button size="small" @click="router.push('/result')">再次试用</el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Row 2: Cart & Favorites -->
      <div class="card-grid">
        <div class="profile-card cart-card">
          <div class="card-header">
            <h3>购物车</h3>
            <el-button type="primary" link v-if="cartItems.length > 0">去结算</el-button>
          </div>
          <div class="cart-content">
            <div v-if="cartItems.length === 0" class="empty-action-area">
              <div class="empty-icon">
                <el-icon :size="40"><ShoppingCart /></el-icon>
              </div>
              <p>购物车空空如也，快去为自己挑点装备吧</p>
              <div class="action-buttons">
                <el-button type="primary" @click="router.push('/shop')">去看推荐商品</el-button>
                <el-button @click="router.push('/result')">去试妆</el-button>
              </div>
            </div>
          </div>
        </div>

        <div class="profile-card favorite-card">
          <div class="card-header">
            <h3>种草单品</h3>
            <el-button type="primary" link>查看全部</el-button>
          </div>
          <div class="favorite-content">
            <el-empty description="还没有收藏任何单品喔" :image-size="60">
              <el-button type="success" plain @click="router.push('/shop')">去逛逛商城</el-button>
            </el-empty>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { MagicStick, Plus, ShoppingCart, Camera, Iphone, Edit } from '@element-plus/icons-vue'
import { getUserInfoApi, getUserImagesApi, uploadAvatarApi, updateNicknameApi, type UserInfoData } from '@/api/user'
import { ElMessage } from 'element-plus'

const router = useRouter()

// 用户信息
const userInfo = reactive<Partial<UserInfoData> & { season?: string }>({
  nickname: '',
  avatar: '',
  phone: '',
  season_type: ''
})

// 昵称编辑状态
const isEditingNickname = ref(false)
const editNicknameValue = ref('')
const nicknameInputRef = ref<any>(null)

const startEditNickname = () => {
  editNicknameValue.value = userInfo.nickname || ''
  isEditingNickname.value = true
  nextTick(() => {
    nicknameInputRef.value?.focus()
  })
}

const saveNickname = async () => {
  if (!isEditingNickname.value) return
  const newNickname = editNicknameValue.value.trim()
  if (!newNickname || newNickname === userInfo.nickname) {
    isEditingNickname.value = false
    return
  }
  
  console.log('>>> [Debug] 开始修改昵称:', newNickname)
  try {
    const res = await updateNicknameApi({ nickname: newNickname })
    console.log('>>> [Debug] 修改昵称响应:', res)
    if (res.code === 200) {
      userInfo.nickname = newNickname
      ElMessage.success('昵称修改成功')
    }
  } catch (error) {
    console.error('>>> [Debug] 修改昵称异常:', error)
    ElMessage.error('昵称修改失败')
  } finally {
    isEditingNickname.value = false
  }
}

// 用户图片
const userImages = ref<any[]>([])

// 保存的方案 (目前仍使用 Mock，若后端有接口可替换为 getMakeupSchemesApi)
const savedPlans = ref([
  {
    id: 1,
    name: '清爽通透男大妆',
    scene: '日常通勤',
    reason: '底妆自然，遮瑕到位，适合每天上学或轻度通勤，不会有明显妆感。',
    cover: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=300&q=80',
    itemCount: 4
  },
  {
    id: 2,
    name: '气场全开职场装',
    scene: '商务稳重',
    reason: '加强眉毛立体感与灰棕色修容，适合见客户与重要商务演讲。',
    cover: 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=300&q=80',
    itemCount: 5
  }
])

const cartItems = ref([])

// 加载数据
const loadUserData = async () => {
  console.log('>>> [Debug] 开始同步远程 Mock 数据...')
  try {
    const infoRes = await getUserInfoApi()
    console.log('>>> [Debug] 获取当前用户信息全量响应:', infoRes)
    if (infoRes.code === 200) {
      console.log('>>> [Debug] 提取到的 season_type:', infoRes.data.season_type)
      Object.assign(userInfo, infoRes.data)
      // 兼容性处理：有些 Mock 可能返回 season 字段
      if (!userInfo.season_type && (infoRes.data as any).season) {
        userInfo.season_type = (infoRes.data as any).season
      }
    }

    const imgRes = await getUserImagesApi(10)
    console.log('>>> [Debug] 获取用户图片列表响应:', imgRes)
    if (imgRes.code === 200) {
      userImages.value = imgRes.data.items
    }
  } catch (error) {
    console.error('>>> [Debug] 接口调用异常:', error)
    ElMessage.error('获取用户信息失败，请检查网络或登录状态')
  }
}

// 处理头像上传
const handleAvatarUpload = async (options: any) => {
  console.log('>>> [Debug] 开始上传头像:', options.file.name)
  try {
    const res = await uploadAvatarApi(options.file)
    console.log('>>> [Debug] 上传头像响应:', res)
    if (res.code === 200) {
      userInfo.avatar = res.data.avatar
      ElMessage.success('头像上传成功')
    }
  } catch (error) {
    console.error('>>> [Debug] 头像上传异常:', error)
    ElMessage.error('头像上传失败')
  }
}

onMounted(() => {
  loadUserData()
})

const handleCart = (plan: any) => {
  ElMessage.success(`方案 ${plan.name} 的关联商品已加入购物车！`)
}
</script>

<style scoped>
.profile-container {
  min-height: 100vh;
  background: #f8fafc;
  padding: 40px;
  font-family: 'Outfit', sans-serif;
}

.profile-header {
  max-width: 1200px;
  margin: 0 auto 30px;
  background: #fff;
  border-radius: 20px;
  padding: 30px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.03);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 25px;
}

.user-avatar {
  border: 4px solid #f1f5f9;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  cursor: pointer;
}

.avatar-uploader {
  position: relative;
}

.avatar-hover-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(0,0,0,0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.avatar-uploader:hover .avatar-hover-mask {
  opacity: 1;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-name-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-name {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.nickname-input {
  width: 200px;
}

.nickname-input :deep(.el-input__inner) {
  font-size: 24px;
  font-weight: 700;
  height: 40px;
}

.edit-icon {
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  transition: color 0.2s;
}

.edit-icon:hover {
  color: #3b82f6;
}

.user-tags {
  display: flex;
  gap: 12px;
}

.season-tag, .status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.season-tag {
  background: #FEF3C7;
  color: #D97706;
}

.season-tag.placeholder {
  background: #f1f5f9;
  color: #94a3b8;
  opacity: 0.6;
}

.phone-tag {
  background: #f1f5f9;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.profile-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
}

.profile-card {
  background: #fff;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.03);
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-header h3 {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.card-desc {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 20px 0;
}

.photo-list {
  display: flex;
  gap: 15px;
  overflow-x: auto;
  padding-bottom: 10px;
}

.photo-item {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-label {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  backdrop-filter: blur(4px);
}

.photo-label.success {
  background: rgba(16, 185, 129, 0.85); /* emerald-500 */
}

.photo-label.pending {
  background: rgba(245, 158, 11, 0.85); /* amber-500 */
}

.upload-item {
  border: 2px dashed #cbd5e1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
  background: #f8fafc;
}

.upload-item:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background: #eff6ff;
}

.upload-item .el-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.empty-action-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 0;
  text-align: center;
}

.empty-icon {
  color: #cbd5e1;
  margin-bottom: 16px;
}

.empty-action-area p {
  color: #64748b;
  font-size: 14px;
  margin-bottom: 24px;
}

.action-buttons {
  display: flex;
  gap: 16px;
}

.plan-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 8px;
}

.plan-item {
  display: flex;
  gap: 16px;
  background: #f8fafc;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #f1f5f9;
  transition: all 0.2s;
}

.plan-item:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.plan-cover {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
}

.plan-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.scene-tag-overlay {
  position: absolute;
  top: 4px;
  left: 4px;
  background: rgba(0,0,0,0.6);
  color: #fff;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  backdrop-filter: blur(2px);
}

.plan-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.plan-info h4 {
  margin: 0 0 6px 0;
  font-size: 15px;
  color: #1e293b;
}

.plan-reason {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.plan-meta {
  font-size: 11px;
  color: #3b82f6;
  margin: 4px 0 0 0;
  font-weight: 600;
}

.plan-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
</style>
