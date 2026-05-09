from fastapi import APIRouter, Depends, Query
from typing import Dict, Any

router = APIRouter(prefix="/api/llm", tags=["llm"])

def _api_success(data: Any, message: str = "success", code: int = 0) -> Dict[str, Any]:
    return {"code": code, "message": message, "data": data}

def _api_error(error_code: str, message: str, status_code: int = 400) -> Dict[str, Any]:
    return {"code": status_code, "message": message, "data": None, "error_code": error_code}

@router.get("/season_description", summary="生成季型描述文案")
async def get_llm_season_description(
    season_type: str = Query(default="warm_autumn", description="季型"),
):
    try:
        from llm_deepseek import get_llm_instance
        llm = get_llm_instance()
        description = llm.generate_pca_description(season_type)
        return _api_success({"season_type": season_type, "description": description})
    except Exception as e:
        return _api_error("LLM_ERROR", f"生成描述失败: {str(e)}", 500)

@router.get("/style_features", summary="生成风格特征建议")
async def get_llm_style_features(
    season_type: str = Query(default="warm_autumn", description="季型"),
    style: str = Query(default="clean", description="妆容风格"),
):
    try:
        from llm_deepseek import get_llm_instance
        llm = get_llm_instance()
        features = llm.generate_style_features(season_type, style)
        return _api_success({"season_type": season_type, "style": style, "features": features})
    except Exception as e:
        return _api_error("LLM_ERROR", f"生成特征建议失败: {str(e)}", 500)

@router.get("/product_recommendation", summary="生成产品推荐理由")
async def get_llm_product_recommendation(
    product_name: str = Query(default="", description="产品名称"),
    season_type: str = Query(default="warm_autumn", description="季型"),
    color_info: str = Query(default="", description="色号信息"),
):
    try:
        from llm_deepseek import get_llm_instance
        llm = get_llm_instance()
        reason = llm.generate_product_recommendation(product_name, season_type, color_info)
        return _api_success({"product_name": product_name, "season_type": season_type, "recommendation": reason})
    except Exception as e:
        return _api_error("LLM_ERROR", f"生成推荐理由失败: {str(e)}", 500)
