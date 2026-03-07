<template>
  <div class="galaxy-background" ref="container">
    <canvas ref="canvas"></canvas>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const container = ref<HTMLElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let animationFrameId: number

interface Star {
  x: number
  y: number
  z: number
  size: number
  color: string
}

const stars: Star[] = []
const STAR_COUNT = 1500
const SPEED = 0.5
const DEPTH = 1000

const initStars = (width: number, height: number) => {
  stars.length = 0
  for (let i = 0; i < STAR_COUNT; i++) {
    stars.push({
      x: (Math.random() - 0.5) * width * 2,
      y: (Math.random() - 0.5) * height * 2,
      z: Math.random() * DEPTH,
      size: Math.random() * 2,
      color: getRandomColor()
    })
  }
}

const getRandomColor = () => {
  const colors = [
    'rgba(255, 255, 255, 0.8)', // White
    'rgba(173, 216, 230, 0.8)', // Light Blue
    'rgba(255, 182, 193, 0.8)', // Light Pink
    'rgba(221, 160, 221, 0.8)', // Plum
    'rgba(135, 206, 250, 0.8)'  // Light Sky Blue
  ]
  const index = Math.floor(Math.random() * colors.length)
  return colors[index]!
}

const props = defineProps({
  paused: {
    type: Boolean,
    default: false
  }
})

const animate = () => {
  if (!canvas.value || !ctx) return
  const width = canvas.value.width
  const height = canvas.value.height
  const cx = width / 2
  const cy = height / 2

  ctx.fillStyle = 'rgba(10, 10, 30, 0.2)' // Trail effect
  ctx.fillRect(0, 0, width, height)

  stars.forEach(star => {
    // Move star towards viewer only if not paused
    if (!props.paused) {
      star.z -= SPEED
      if (star.z <= 0) {
        star.z = DEPTH
        star.x = (Math.random() - 0.5) * width * 2
        star.y = (Math.random() - 0.5) * height * 2
      }
    }

    // Project 3D coordinates to 2D
    const k = 128.0 / star.z
    const px = star.x * k + cx
    const py = star.y * k + cy

    if (px >= 0 && px <= width && py >= 0 && py <= height) {
      const size = (1 - star.z / DEPTH) * star.size * 2
      const alpha = (1 - star.z / DEPTH)
      
      ctx!.beginPath()
      ctx!.arc(px, py, size, 0, Math.PI * 2)
      ctx!.fillStyle = star.color.replace('0.8)', `${alpha})`)
      ctx!.fill()
    }
  })

  animationFrameId = requestAnimationFrame(animate)
}

const handleResize = () => {
  if (!container.value || !canvas.value) return
  canvas.value.width = container.value.clientWidth
  canvas.value.height = container.value.clientHeight
  initStars(canvas.value.width, canvas.value.height)
}

onMounted(() => {
  if (canvas.value && container.value) {
    ctx = canvas.value.getContext('2d')
    handleResize()
    window.addEventListener('resize', handleResize)
    animate()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  cancelAnimationFrame(animationFrameId)
})
</script>

<style scoped>
.galaxy-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  background: radial-gradient(ellipse at bottom, #1b2735 0%, #090a0f 100%);
  overflow: hidden;
}
</style>
