<template>
  <div class="parameter-panel">
    <div class="panel-header">
      <h3>妆容定制</h3>
    </div>
    
    <div class="panel-content">
      <div class="control-group">
        <div class="label-row">
          <span>妆容风格</span>
        </div>
        <el-select v-model="localParams.style" placeholder="选择风格" @change="handleChange">
          <el-option label="自然清透" value="clean" />
          <el-option label="轻熟职场" value="business" />
          <el-option label="韩系潮流" value="idol" />
        </el-select>
      </div>

      <!-- New Module: Cosmetic Product Testing -->
      <div class="control-group">
        <div class="label-row">
          <span>产品试妆</span>
          <el-tag size="small" type="warning" effect="dark" style="transform: scale(0.8)">New</el-tag>
        </div>
        <div class="product-test-card" @click="handleProductTest">
          <div class="icon-wrapper">
             <el-icon><Brush /></el-icon>
          </div>
          <div class="text-content">
            <span class="main-text">化妆品上脸测试</span>
            <span class="sub-text">上传单品看效果</span>
          </div>
          <el-icon class="arrow-icon"><ArrowRight /></el-icon>
        </div>
      </div>

      <div class="action-group">
        <el-button type="primary" class="action-btn" @click="handleApply" :loading="loading">
          生成妆容
        </el-button>
        <el-button class="action-btn" @click="handleReset">
          重置
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { Brush, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

defineProps<{
  loading?: boolean
}>()

const emit = defineEmits(['update:params', 'apply', 'reset'])

const localParams = reactive({
  style: 'clean'
})

const handleChange = () => {
  emit('update:params', { ...localParams })
}

const handleApply = () => {
  emit('apply')
}

const handleReset = () => {
  localParams.style = 'clean'
  handleChange()
  emit('reset')
}

const handleProductTest = () => {
  ElMessage.warning('该功能开发中，敬请期待')
}
</script>

<style scoped>
.parameter-panel {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 20px;
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.panel-header h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 10px;
}

.control-group {
  margin-bottom: 24px;
}

.label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
}

.desc {
  font-size: 12px;
  color: #888;
  margin: 0;
}

.value {
  color: #409eff;
}

.action-group {
  display: flex;
  gap: 10px;
  margin-top: 30px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 20px;
}

.action-btn {
  flex: 1;
}

/* Product Test Card Styles */
.product-test-card {
  background: rgba(255, 255, 255, 0.08); /* Slightly lighter than panel */
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.product-test-card:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: translateY(-2px);
  border-color: #e6a23c; /* Warning color accent */
}

.icon-wrapper {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #e6a23c 0%, #f56c6c 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: white;
}

.text-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.main-text {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
}

.sub-text {
  font-size: 12px;
  color: #aaa;
}

.arrow-icon {
  color: #666;
  font-size: 14px;
}

.product-test-card:hover .arrow-icon {
  color: #fff;
}
</style>
