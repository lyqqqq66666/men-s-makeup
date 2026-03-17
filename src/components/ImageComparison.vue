<template>
  <div class="image-comparison" ref="container" @mousemove="handleMouseMove" @touchmove="handleTouchMove">
    <div class="image-wrapper before">
      <img :src="beforeImage" alt="Before" />
      <span class="label">原图 (Before)</span>
    </div>
    <div 
      class="image-wrapper after" 
      :style="{ clipPath: `inset(0 ${100 - sliderPosition}% 0 0)` }"
    >
      <img :src="afterImage" alt="After" />
      <span class="label">效果图 (After)</span>
    </div>
    <div class="slider-handle" :style="{ left: sliderPosition + '%' }" @mousedown="startDrag" @touchstart="startDrag">
      <div class="slider-line"></div>
      <div class="slider-button">
        <el-icon><DCaret /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { DCaret } from '@element-plus/icons-vue'

defineProps<{
  beforeImage: string
  afterImage: string
}>()

const sliderPosition = ref(50)
const container = ref<HTMLElement | null>(null)
const isDragging = ref(false)

const startDrag = () => {
  isDragging.value = true
}

const stopDrag = () => {
  isDragging.value = false
}

const handleMove = (clientX: number) => {
  if (!isDragging.value || !container.value) return
  
  const rect = container.value.getBoundingClientRect()
  const x = clientX - rect.left
  const width = rect.width
  
  let pos = (x / width) * 100
  pos = Math.max(0, Math.min(100, pos))
  
  sliderPosition.value = pos
}

const handleMouseMove = (e: MouseEvent) => {
  handleMove(e.clientX)
}

const handleTouchMove = (e: TouchEvent) => {
  const touch = e.touches[0]
  if (touch) {
    handleMove(touch.clientX)
  }
}

// Global event listeners for stopping drag
window.addEventListener('mouseup', stopDrag)
window.addEventListener('touchend', stopDrag)
</script>

<style scoped>
/* Resetting styles for the clip-path approach */
.image-comparison {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 250px;
  overflow: hidden;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.2); /* Darker background */
  box-shadow: inset 0 0 20px rgba(0,0,0,0.2);
}

.image-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.image-wrapper img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.image-wrapper.after {
  z-index: 2;
}

.slider-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 4px;
  background: #fff; /* White line */
  z-index: 3;
  cursor: col-resize;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 0 0 10px rgba(0,0,0,0.2);
}

.slider-button {
  width: 40px; /* Larger button */
  height: 40px;
  border-radius: 50%;
  background: #fff;
  color: #409eff; /* Brand color */
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  border: 2px solid rgba(255, 255, 255, 0.1);
}

.label {
  position: absolute;
  top: 12px;
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.9);
  color: #333;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  z-index: 10;
}

.before .label {
  left: 20px; /* Changed to left for visibility */
}

.after .label {
  right: 20px; /* Changed to right for visibility */
}
</style>
