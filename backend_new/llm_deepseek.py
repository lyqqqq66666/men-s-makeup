"""
DeepSeek LLM 集成模块
用于风格推荐文案生成、用户咨询问答等功能

使用方法：
1. 设置环境变量：export DEEPSEEK_API_KEY="your-api-key"
2. 或在代码中调用：llm.set_api_key("your-api-key")
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class DeepSeekLLM:
    """DeepSeek 大语言模型集成类"""
    
    _instance = None
    
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    SEASON_PROMPTS = {
        "warm_spring": "暖春型 - 温暖、明亮、充满活力",
        "warm_autumn": "暖秋型 - 温暖、深沉、成熟稳重",
        "cool_summer": "冷夏型 - 冷调、柔和、清爽干净",
        "cool_winter": "冷冬型 - 冷调、鲜明、锐利有型"
    }
    
    STYLE_PROMPTS = {
        "clean": "清爽自然妆容适合日常出行，注重皮肤质感护理，突出清新阳光的气质。",
        "business": "职场妆容需要干练利落，建议使用哑光底妆产品，眉部要整齐干净，整体展现专业自信形象。",
        "idol": "韩系妆容追求精致亮眼，建议使用提亮产品打造立体轮廓，眼部和唇部可适当加强色彩。"
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeepSeekLLM, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.api_key = os.environ.get('DEEPSEEK_API_KEY', 'sk-ba819c097197479b9e4290e558b9cbfb')
        if not self.api_key:
            logger.warning("DeepSeek API Key 未设置")
    
    def set_api_key(self, api_key: str):
        """设置API密钥"""
        self.api_key = api_key
    
    def _call_api(self, messages: List[Dict], model: str = "deepseek-chat", 
                  temperature: float = 0.7, max_tokens: int = 1000) -> Optional[str]:
        """调用DeepSeek API"""
        if not self.api_key:
            return None
        
        try:
            import httpx
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    self.API_URL,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            return None
    
    def generate_pca_description(self, season_type: str, user_features: Optional[Dict] = None) -> str:
        """
        生成PCA季型分析描述
        
        Args:
            season_type: 季型，如 "warm_autumn", "cool_winter"
            user_features: 用户特征（可选）
        
        Returns:
            个性化的季型描述文案
        """
        
        system_prompt = """你是一位专业的男士形象色彩顾问，擅长根据用户的季型特征，
        生成专业、贴心、有说服力的个性化描述。

        你的描述要：
        1. 突出用户季型的独特魅力
        2. 语言专业但亲切
        3. 强调适合的色彩如何衬托气质
        4. 适合18-35岁男性读者
        5. 控制在150字以内"""
        
        season_desc = self.SEASON_PROMPTS.get(season_type, "综合型")
        
        user_context = ""
        if user_features:
            user_context = f"""
用户特征参考：
- 肤色：{user_features.get('skin_tone', '自然')}
- 发色：{user_features.get('hair_color', '自然黑')}
- 眼睛：{user_features.get('eye_color', '自然色')}
- 气质：{user_features.get('vibe', '普通')}"""
        
        user_prompt = f"""请为用户生成一段季型分析描述。

季型：{season_desc}{user_context}

要求：
1. 描述用户的色彩特征（如"如成熟秋枫般稳重、深邃"）
2. 说明适合的色彩为什么能衬托气质
3. 强调这种风格的独特魅力
4. 字数控制在150字以内"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self._call_api(messages, temperature=0.7, max_tokens=300) or self._default_season_description(season_type)
    
    def generate_style_features(self, season_type: str, style: str = "clean") -> List[str]:
        """
        生成风格特征建议
        
        Args:
            season_type: 季型
            style: 妆容风格
        
        Returns:
            建议列表，如 ["底妆建议：选择自然偏暖...", "眉毛建议：深棕色..."]
        """
        
        system_prompt = """你是一位专业的男士形象顾问，擅长生成实用的妆容和穿搭建议。

请生成3条针对性的建议：
1. 底妆建议
2. 眉毛建议
3. 穿搭色彩建议

每条建议要：
- 具体且可操作
- 符合男士审美（自然、不夸张）
- 符合季节特征
- 格式简洁，每条不超过30字"""
        
        season_desc = self.SEASON_PROMPTS.get(season_type, "综合型")
        
        user_prompt = f"""请为{season_desc}男士生成3条形象建议：
1. 底妆建议
2. 眉毛建议  
3. 穿搭色彩建议

请用列表格式返回，每条建议20-30字。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        result = self._call_api(messages, temperature=0.7, max_tokens=200)
        
        if result:
            features = []
            for line in result.split('\n'):
                line = line.strip()
                if line and (line.startswith('1') or line.startswith('•') or line.startswith('-')):
                    features.append(line.lstrip('123456789.-•、').strip())
            if len(features) >= 3:
                return features[:3]
        
        return self._default_features(season_type)
    
    def generate_product_recommendation(self, product_name: str, season_type: str, 
                                      color_info: str) -> str:
        """
        生成产品推荐理由
        
        Args:
            product_name: 产品名称
            season_type: 季型
            color_info: 色号信息
        
        Returns:
            产品推荐理由文案
        """
        
        system_prompt = """你是一位专业的美妆产品推荐师，擅长撰写有说服力的产品推荐理由。

你的推荐要：
1. 突出产品与用户季型的匹配度
2. 说明为什么适合
3. 强调使用效果
4. 语言简洁有力
5. 控制在50字以内"""
        
        season_desc = self.SEASON_PROMPTS.get(season_type, "综合型")
        
        user_prompt = f"""为{season_desc}用户推荐产品：

产品：{product_name}
色号：{color_info}

请生成一段50字以内的推荐理由。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self._call_api(messages, temperature=0.8, max_tokens=100) or f"适合{season_desc}的{product_name}，{color_info}色号自然协调。"
    
    def _default_season_description(self, season_type: str) -> str:
        """默认季型描述（当API不可用时）"""
        
        defaults = {
            "warm_spring": "您的面部色彩重心偏暖且明亮，呈现出如春日暖阳般活力、健康的质感。适合带有暖调、鲜明感的色彩，能完美衬托出男性的阳光魅力。",
            "warm_autumn": "您的面部色彩重心偏暖且柔和，呈现出如成熟秋枫般稳重、深邃的质感。适合带有大地色调、低饱和度却具有包容感的色彩，能完美衬托出男性内敛且高级的魅力。",
            "cool_summer": "您的面部色彩重心偏冷且柔和，呈现出如夏日晴空般清爽、干净的质感。适合带有冷调、柔和感的色彩，能完美衬托出男性的清新气质。",
            "cool_winter": "您的面部色彩重心偏冷且鲜明，呈现出如冬日寒梅般锐利、独特的质感。适合带有冷调、高对比度的色彩，能完美衬托出男性的强大气场。"
        }
        
        return defaults.get(season_type, "您的面部色彩独特而有个性，适合多种色系选择。")
    
    def _default_features(self, season_type: str) -> List[str]:
        """默认特征建议（当API不可用时）"""
        
        defaults = {
            "warm_spring": [
                "底妆建议：选择自然偏暖、轻微遮瑕的粉底，避免过白。",
                "眉毛建议：浅棕或自然黑色，强调柔和眉形。",
                "穿搭色彩：暖橘、米白、浅黄等明亮暖色。"
            ],
            "warm_autumn": [
                "底妆建议：选择自然偏暖、哑光质地的粉底，避免假白。",
                "眉毛建议：深棕色或灰褐色，强调毛流感。",
                "穿搭色彩：大地色系、卡其色、军绿色等低亮度暖色。"
            ],
            "cool_summer": [
                "底妆建议：选择自然偏冷、轻薄质地的粉底，追求透明感。",
                "眉毛建议：深灰或冷棕色，保持自然眉形。",
                "穿搭色彩：灰蓝、淡紫、浅粉等柔和冷色。"
            ],
            "cool_winter": [
                "底妆建议：选择自然偏白、高遮瑕的粉底，打造精致感。",
                "眉毛建议：纯黑或深灰色，眉毛要整齐有型。",
                "穿搭色彩：酒红、深蓝、黑色等高对比冷色。"
            ]
        }
        
        return defaults.get(season_type, [
            "底妆建议：选择自然质地的粉底，追求干净效果。",
            "眉毛建议：保持自然眉形，颜色与发色协调。",
            "穿搭色彩：选择与季型匹配的色彩系列。"
        ])


def get_llm_instance() -> DeepSeekLLM:
    """获取LLM单例实例"""
    return DeepSeekLLM()


if __name__ == "__main__":
    llm = get_llm_instance()
    print("DeepSeek LLM 模块已加载")
    
    if llm.api_key:
        print("API Key 已配置")
        test_desc = llm.generate_pca_description("warm_autumn")
        print(f"测试季型描述: {test_desc[:100]}...")
        
        test_features = llm.generate_style_features("warm_autumn")
        print(f"测试特征建议: {test_features}")
    else:
        print("请设置 DEEPSEEK_API_KEY 环境变量")
