from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from timetable_generator import timetable_generator

app = FastAPI(
    title="AI Timetable Generator"
)

@app.get("/generate-timetable/")
def generate_timetable(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD")
):
    """
    Generate timetable for the specified date range (only weekdays).
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if start > end:
            return {"error": "start_date must be earlier than end_date"}

        # Generate weekday indices (0=Mon, ..., 4=Fri)
        weekday_indices = []
        curr = start
        while curr <= end:
            if curr.weekday() < 5:  # Ignore weekends
                weekday_indices.append(curr.weekday())
            curr += timedelta(days=1)

        if not weekday_indices:
            return {"error": "No weekdays found in the given date range."}

        # Remove duplicates and sort
        unique_days = sorted(set(weekday_indices))

        # Call timetable generator
        timetable = timetable_generator(days=unique_days)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "generated_days": len(unique_days),
            "timetable": timetable
        }

    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}