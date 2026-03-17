<template>
  <div class="profile-container">
    <div class="profile-header">
      <div class="user-info">
        <el-avatar :size="80" src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png" class="user-avatar" />
        <div class="user-details">
          <h2 class="user-name">智颜体验官</h2>
          <div class="user-tags">
            <span class="season-tag"><el-icon><MagicStick /></el-icon> 温润秋季型</span>
            <span class="status-tag"><el-icon><Select /></el-icon> 今日诊断完成</span>
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
            <el-button type="primary" link>查看全部</el-button>
          </div>
          <p class="card-desc">管理您的每一次颜值升级</p>
          <div class="photo-list">
            <div class="photo-item">
              <img src="https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&q=80" alt="photo1" />
              <div class="photo-label success">已诊断 - 暖秋型</div>
            </div>
            <div class="photo-item">
              <img src="https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=200&q=80" alt="photo2" />
              <div class="photo-label pending">待诊断</div>
            </div>
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { MagicStick, Select, Plus, ShoppingCart } from '@element-plus/icons-vue'

const router = useRouter()
import { ElMessage } from 'element-plus'

// Mock logic
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
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-name {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
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

.status-tag {
  background: #ECFDF5;
  color: #059669;
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
