
from fastapi import APIRouter

from app.core.responses import success_response
from app.schemas.analysis import HeatwaveAnalysisRequest
from app.services.analysis_service import analyze_heatwaves

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.post("/heatwaves")
async def heatwave_analysis_endpoint(
    request: HeatwaveAnalysisRequest,
):
    result = await analyze_heatwaves(request)

    return success_response(
        "Heatwave analysis completed successfully",
        result,
    )
