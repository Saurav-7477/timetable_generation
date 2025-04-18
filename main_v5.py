from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from timetable_generator_v2 import timetable_generator

app = FastAPI(title="AI Timetable Generator")

@app.get("/generate-timetable/")
def generate_timetable(
    class_name: str = Query(..., description="Class name (e.g., 8 th)"),
    division_name: str = Query(..., description="Division name (e.g., Div - A)"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD")
):
    """
    Generate timetable for the specified class/division and date range (weekdays only).
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if start > end:
            return {"error": "start_date must be earlier than end_date"}

        # Collect weekdays for each week
        curr = start
        weeks = {}
        while curr <= end:
            year_week = curr.isocalendar()[:2]  # (year, week_number)
            if curr.weekday() < 5:  # 0=Monday ... 4=Friday
                weeks.setdefault(year_week, []).append(curr.weekday())
            curr += timedelta(days=1)

        if not weeks:
            return {"error": "No weekdays found in the given date range."}

        result = {}
        for (year, week), weekdays in weeks.items():
            timetable = timetable_generator(
                days=sorted(set(weekdays)),
                class_name=class_name.strip(),
                division_name=division_name.strip()
            )
            result[f"Week {week} ({year})"] = timetable

        class_division_key=class_name+division_name
        return {
            "class": class_name,
            "division": division_name,
            "start_date": start_date,
            "end_date": end_date,
            "weeks_generated": len(result),
            "timetable": result
        }

    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}