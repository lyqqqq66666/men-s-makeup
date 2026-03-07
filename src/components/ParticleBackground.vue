<template>
  <div class="particle-background" ref="container">
    <canvas ref="canvas"></canvas>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const container = ref<HTMLElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let animationFrameId: number
let particles: Particle[] = []

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  update(w: number, h: number): void
  draw(ctx: CanvasRenderingContext2D): void
}

const props = defineProps({
  color: {
    type: String,
    default: 'rgba(255, 255, 255, 0.5)'
  },
  lineColor: {
    type: String,
    default: 'rgba(255, 255, 255, 0.1)'
  },
  particleCount: {
    type: Number,
    default: 80
  }
})

class ParticleImpl implements Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  
  constructor(w: number, h: number) {
    this.x = Math.random() * w
    this.y = Math.random() * h
    this.vx = (Math.random() - 0.5) * 1.5
    this.vy = (Math.random() - 0.5) * 1.5
    this.size = Math.random() * 3 + 1
  }

  update(w: number, h: number) {
    this.x += this.vx
    this.y += this.vy

    if (this.x < 0 || this.x > w) this.vx *= -1
    if (this.y < 0 || this.y > h) this.vy *= -1
  }

  draw(ctx: CanvasRenderingContext2D) {
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = props.color
    ctx.fill()
  }
}

const initParticles = (width: number, height: number) => {
  particles = []
  for (let i = 0; i < props.particleCount; i++) {
    particles.push(new ParticleImpl(width, height))
  }
}

const animate = () => {
  if (!canvas.value || !ctx) return
  const width = canvas.value.width
  const height = canvas.value.height
  
  ctx.clearRect(0, 0, width, height)
  
  // Update and draw particles
  particles.forEach(p => {
    p.update(width, height)
    p.draw(ctx!)
  })

  // Draw connections
  particles.forEach((a, index) => {
    for (let i = index + 1; i < particles.length; i++) {
      const b = particles[i]
      if (!b) continue
      
      const dx = a.x - b.x
      const dy = a.y - b.y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < 150) {
        ctx!.beginPath()
        ctx!.strokeStyle = props.lineColor
        ctx!.lineWidth = 1
        ctx!.moveTo(a.x, a.y)
        ctx!.lineTo(b.x, b.y)
        ctx!.stroke()
      }
    }
  })

  animationFrameId = requestAnimationFrame(animate)
}

const handleResize = () => {
  if (!container.value || !canvas.value) return
  canvas.value.width = container.value.clientWidth
  canvas.value.height = container.value.clientHeight
  initParticles(canvas.value.width, canvas.value.height)
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
.particle-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none; /* Allow clicks to pass through */
}
</style>
