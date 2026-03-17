import fs from 'fs'
import path from 'path'
import sharp from 'sharp'

// 配置需要扫描压缩的目录
const directories = [
  'public/images/styles',
  'src/assets/login'
]

// 限制最大宽度，超过此宽度将等比例缩小
const MAX_WIDTH = 1200

async function processDirectory(dir) {
  const absolutePath = path.resolve(dir)
  if (!fs.existsSync(absolutePath)) {
    console.warn(`目录不存在: ${absolutePath}`)
    return
  }

  const files = fs.readdirSync(absolutePath)
  for (const file of files) {
    if (!file.match(/\.(png|jpg|jpeg)$/i)) continue
    
    // 跳过已经压缩过的文件
    if (file.includes('.min.')) continue

    const filePath = path.join(absolutePath, file)
    const stats = fs.statSync(filePath)
    
    // 如果文件大于 500KB，则进行压缩
    if (stats.size > 500 * 1024) {
      console.log(`正在压缩: ${filePath} (${(stats.size / 1024 / 1024).toFixed(2)} MB)`)
      
      const tmpPath = filePath + '.tmp'
      
      try {
        await sharp(filePath)
          .resize({ width: MAX_WIDTH, withoutEnlargement: true })
          .png({ quality: 70, effort: 8 }) // 高压缩率
          .toFile(tmpPath)
          
        const newStats = fs.statSync(tmpPath)
        console.log(`压缩完成: ${(newStats.size / 1024 / 1024).toFixed(2)} MB `)
        
        // 覆盖原文件
        fs.renameSync(tmpPath, filePath)
      } catch (err) {
        console.error(`处理失败 ${file}:`, err)
        if (fs.existsSync(tmpPath)) {
          fs.unlinkSync(tmpPath)
        }
      }
    }
  }
}

async function start() {
  console.log('开始扫描并压缩大体积图片...')
  for (const dir of directories) {
    await processDirectory(dir)
  }
  console.log('图片压缩任务全部完成！')
}

start()
