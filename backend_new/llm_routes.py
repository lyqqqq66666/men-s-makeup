"""
LLM API 路由模块
集成 DeepSeek LLM 到 FastAPI 应用

使用方法：
在 fastapi_app.py 中导入并注册：
    from llm_routes import router as llm_router
    app.include_router(llm_router)

或在文件末尾添加：
    from llm_deepseek import get_llm_instance
    llm = get_llm_instance()
"""

from fastapi import APIRouter, Depends, Query
from typing import Dict, Any

router = APIRouter(prefix="/api/llm", tags=["llm"])


def _api_success(data: Any, message: str = "success", code: int = 0) -> Dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def _api_error(error_code: str, message: str, status_code: int = 400) -> Dict[str, Any]:
    return {"code": status_code, "message": message, "data": None, "error_code": error_code}


def get_current_user_placeholder():
    """占位符 - 实际在 fastapi_app.py 中定义"""
    return {"user_id": "placeholder"}


@router.get("/season_description", summary="生成季型描述文案")
async def get_llm_season_description(
    season_type: str = Query(default="warm_autumn", description="季型: warm_spring, warm_autumn, cool_summer, cool_winter"),
    user: Dict[str, Any] = Depends(get_current_user_placeholder)
):
    """
    使用 DeepSeek LLM 生成个性化的季型分析描述
    
    Args:
        season_type: 季型（warm_spring, warm_autumn, cool_summer, cool_winter）
        user: 当前登录用户
    
    Returns:
        个性化的季型描述文案
    """
    try:
        from llm_deepseek import get_llm_instance
        llm = get_llm_instance()
        description = llm.generate_pca_description(season_type)
        return _api_success({
            "season_type": season_type,
            "description": description
        })
    except Exception as e:
        return _api_error("LLM_ERROR", f"生成描述失败: {str(e)}", 500)


@router.get("/style_features", summary="生成风格特征建议")
async def get_llm_style_features(
    season_type: str = Query(default="warm_autumn", description="季型"),
    style: str = Query(default="clean", description="妆容风格: clean, business, idol"),
    user: Dict[str, Any] = Depends(get_current_user_placeholder)
):
    """
    使用 DeepSeek LLM 生成个性化的妆容和穿搭建议
    
    Args:
        season_type: 季型
        style: 妆容风格（clean, business, idol）
        user: 当前登录用户
    
    Returns:
        包含3条建议的列表：底妆建议、眉毛建议、穿搭色彩建议
    """
    try:
        from llm_deepseek import get_llm_instance
        llm = get_llm_instance()
        features = llm.generate_style_features(season_type, style)
        return _api_success({
            "season_type": season_type,
            "style": style,
            "features": features
        })
    except Exception as e:
        return _api_error("LLM_ERROR", f"生成特征建议失败: {str(e)}", 500)


@router.get("/product_recommendation", summary="生成产品推荐理由")
async def get_llm_product_recommendation(
    product_name: str = Query(default="", description="产品名称"),
    season_type: str = Query(default="warm_autumn", description="季型"),
    color_info: str = Query(default="", description="色号信息"),
    user: Dict[str, Any] = Depends(get_current_user_placeholder)
):
    """
    使用 DeepSeek LLM 生成产品推荐理由
    
    Args:
        product_name: 产品名称
        season_type: 季型
        color_info: 色号信息
        user: 当前登录用户
    
    Returns:
        产品推荐理由文案
    """
    try:
        from llm_deepseek import get_llm_instance
        llm = get_llm_instance()
        reason = llm.generate_product_recommendation(product_name, season_type, color_info)
        return _api_success({
            "product_name": product_name,
            "season_type": season_type,
            "color_info": color_info,
            "recommendation": reason
        })
    except Exception as e:
        return _api_error("LLM_ERROR", f"生成推荐理由失败: {str(e)}", 500)


if __name__ == "__main__":
    print("LLM API 路由模块已加载")
    print("使用方法：在 fastapi_app.py 中导入并注册路由")
