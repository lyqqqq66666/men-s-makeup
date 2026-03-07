<template>
  <div class="modern-background" ref="container" @mousemove="handleMouseMove" @mouseleave="handleMouseLeave">
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

// Mouse state
const mouse = {
  x: -1000,
  y: -1000,
  radius: 150 // Interaction radius
}

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  color: string
  baseX: number
  baseY: number
  density: number
  update(w: number, h: number): void
  draw(ctx: CanvasRenderingContext2D): void
}

class FluidParticle implements Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  color: string
  baseX: number
  baseY: number
  density: number
  
  constructor(w: number, h: number) {
    this.x = Math.random() * w
    this.y = Math.random() * h
    this.baseX = this.x
    this.baseY = this.y
    this.vx = (Math.random() - 0.5) * 0.5
    this.vy = (Math.random() - 0.5) * 0.5
    this.size = Math.random() * 4 + 1
    this.density = (Math.random() * 30) + 1
    // Green/Teal palette
    const colors = ['rgba(16, 185, 129, 0.6)', 'rgba(5, 150, 105, 0.5)', 'rgba(52, 211, 153, 0.4)']
    this.color = colors[Math.floor(Math.random() * colors.length)] || 'rgba(16, 185, 129, 0.6)'
  }

  update(w: number, h: number) {
    // Mouse interaction
    const dx = mouse.x - this.x
    const dy = mouse.y - this.y
    const distance = Math.sqrt(dx * dx + dy * dy)
    const forceDirectionX = dx / distance
    const forceDirectionY = dy / distance
    const maxDistance = mouse.radius
    const force = (maxDistance - distance) / maxDistance
    const directionX = forceDirectionX * force * this.density
    const directionY = forceDirectionY * force * this.density

    if (distance < mouse.radius) {
      // Repulsion effect (Antigravity)
      this.x -= directionX
      this.y -= directionY
    } else {
      // Return to base position / drift
      if (this.x !== this.baseX) {
        const dx = this.x - this.baseX
        this.x -= dx / 10
      }
      if (this.y !== this.baseY) {
        const dy = this.y - this.baseY
        this.y -= dy / 10
      }
    }

    // Add some random drift
    this.baseX += this.vx
    this.baseY += this.vy

    // Boundary check for base position
    if (this.baseX < 0 || this.baseX > w) this.vx *= -1
    if (this.baseY < 0 || this.baseY > h) this.vy *= -1
  }

  draw(ctx: CanvasRenderingContext2D) {
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.fill()
  }
}

const props = withDefaults(defineProps<{
  enableLines?: boolean
}>(), {
  enableLines: true
})

const initParticles = (width: number, height: number) => {
  particles = []
  const count = 120 // Increased density
  for (let i = 0; i < count; i++) {
    particles.push(new FluidParticle(width, height))
  }
}

const animate = () => {
  if (!canvas.value || !ctx) return
  const width = canvas.value.width
  const height = canvas.value.height
  
  ctx.clearRect(0, 0, width, height)
  
  // Draw connecting lines
  ctx.lineWidth = 0.5
  
  for (let i = 0; i < particles.length; i++) {
    const p = particles[i]
    if (!p) continue
    p.update(width, height)
    p.draw(ctx)
    
    if (props.enableLines) {
      // Connect nearby particles
      for (let j = i + 1; j < particles.length; j++) {
        const p2 = particles[j]
        if (!p2) continue

        const dx = p.x - p2.x
        const dy = p.y - p2.y
        const distance = Math.sqrt(dx * dx + dy * dy)
        
        if (distance < 120) {
          ctx.beginPath()
          ctx.strokeStyle = `rgba(16, 185, 129, ${0.15 * (1 - distance / 120)})`
          ctx.moveTo(p.x, p.y)
          ctx.lineTo(p2.x, p2.y)
          ctx.stroke()
        }
      }
    }
  }

  animationFrameId = requestAnimationFrame(animate)
}

const handleMouseMove = (event: MouseEvent) => {
  if (!container.value) return
  const rect = container.value.getBoundingClientRect()
  mouse.x = event.clientX - rect.left
  mouse.y = event.clientY - rect.top
}

const handleMouseLeave = () => {
  mouse.x = -1000
  mouse.y = -1000
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
.modern-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  background: #f8fafc;
  overflow: hidden;
}
</style>
