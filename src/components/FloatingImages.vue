<template>
  <div class="floating-images-container">
    <div 
      v-for="(img, index) in images" 
      :key="index"
      class="floating-item"
      :style="getItemStyle(index)"
    >
      <div class="image-wrapper">
        <!-- Using placeholder images from unsplash for demo purposes -->
        <img :src="img.src" :alt="img.alt" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const images = ref([
  { src: 'public/images/styles/1.png', alt: 'Portrait 1' },
  { src: 'public/images/styles/2.png', alt: 'Portrait 2' },
  { src: 'public/images/styles/3.png', alt: 'Portrait 3' },
  { src: 'public/images/styles/4.png', alt: 'Portrait 4' },
  { src: 'public/images/styles/5.png', alt: 'Portrait 5' },
])

// Define zones to keep center clear (Left 25%-75% is restricted)
// Zones: Top-Left, Top-Right, Mid-Left, Mid-Right, Bottom-Left, Bottom-Right
const zones = [
  { topMin: 5, topMax: 20, leftMin: 5, leftMax: 15 },   // TL
  { topMin: 5, topMax: 20, leftMin: 80, leftMax: 90 },  // TR
  { topMin: 40, topMax: 55, leftMin: 5, leftMax: 15 },  // ML
  { topMin: 40, topMax: 55, leftMin: 80, leftMax: 90 }, // MR
  { topMin: 75, topMax: 85, leftMin: 10, leftMax: 20 }, // BL
  { topMin: 75, topMax: 85, leftMin: 75, leftMax: 85 }, // BR
]

const assignedZones = ref<number[]>([])

onMounted(() => {
  // Shuffle zones
  const indices = zones.map((_, i) => i)
  for (let i = indices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [indices[i], indices[j]] = [indices[j]!, indices[i]!];
  }
  assignedZones.value = indices
})

const getItemStyle = (index: number) => {
  // Get assigned zone or fallback to random if out of bounds
  const assignedIndex = assignedZones.value[index]
  const zoneIndex = assignedIndex !== undefined ? assignedIndex : index % zones.length
  const zone = zones[zoneIndex]

  if (!zone) {
      return { display: 'none' } // Should not happen
  }

  // Random position within the zone
  const top = zone.topMin + Math.random() * (zone.topMax - zone.topMin)
  const left = zone.leftMin + Math.random() * (zone.leftMax - zone.leftMin)
  
  const randomDelay = Math.random() * 5
  const randomDuration = 12 + Math.random() * 8
  
  return {
    top: `${top}%`,
    left: `${left}%`,
    animationDelay: `${randomDelay}s`,
    animationDuration: `${randomDuration}s`
  }
}
</script>

<style scoped>
.floating-images-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  pointer-events: none; /* Allow clicks to pass through */
  z-index: 0;
}

.floating-item {
  position: absolute;
  width: 150px;
  height: 200px;
  opacity: 0;
  animation: float-fade 15s infinite ease-in-out;
  filter: drop-shadow(0 10px 20px rgba(0,0,0,0.3));
}

.image-wrapper {
  width: 100%;
  height: 100%;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.image-wrapper img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

@keyframes float-fade {
  0% {
    transform: translateY(20px) scale(0.9);
    opacity: 0;
  }
  20% {
    transform: translateY(0) scale(1);
    opacity: 0.6;
  }
  50% {
    transform: translateY(-20px) scale(1.05);
    opacity: 0.8;
  }
  80% {
    transform: translateY(-40px) scale(1);
    opacity: 0.6;
  }
  100% {
    transform: translateY(-60px) scale(0.9);
    opacity: 0;
  }
}
</style>
