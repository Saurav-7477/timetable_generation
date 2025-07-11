from fastapi import FastAPI, Query
from typing import Optional
from timetable_generator_v2 import timetable_generator
from mangum import Mangum

app = FastAPI(
    title="AI Timetable Generator API",
    description="Automatically generates weekly school timetables based on inputs.",
    version="1.0.0"
)

@app.get("/generate-timetable/")
def generate_timetable(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    class_name: Optional[str] = Query(None, description="Class name (e.g., '6')")
):
    """
    Generate a timetable for a specific class across all its divisions
    within the provided date range (Monday to Friday each week).
    """
    try:
        result = timetable_generator(start_date=start_date, end_date=end_date, class_name=class_name)
        return result
    except Exception as e:
        return {"error": str(e)}


# AWS Lambda handler
handler = Mangum(app)