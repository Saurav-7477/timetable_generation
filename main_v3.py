from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from timetable_generator import timetable_generator

app = FastAPI(title="AI Timetable Generator")

@app.get("/generate-timetable/")
def generate_timetable(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD"),
    class_name: str = Query(..., description="Class name e.g., '8 th'"),
    division_name: str = Query(..., description="Division name e.g., 'Div - A'")
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if start > end:
            return {"error": "start_date must be earlier than end_date"}

        # Generate list of weekdays within the range
        all_weekdays = []
        current = start
        while current <= end:
            if current.weekday() < 5:
                all_weekdays.append(current)
            current += timedelta(days=1)

        if not all_weekdays:
            return {"error": "No weekdays found in the given date range."}

        # Organize into weeks (chunks of 5 weekdays)
        weeks = [all_weekdays[i:i+5] for i in range(0, len(all_weekdays), 5)]
        timetable_result = {}

        for week_index, week_days in enumerate(weeks):
            weekday_indices = [dt.weekday() for dt in week_days]
            timetable = timetable_generator(
                days=sorted(set(weekday_indices)),
                class_filter=class_name.strip(),
                division_filter=division_name.strip()
            )
            timetable_result[f"Week {week_index+1}"] = timetable

        return {
            "start_date": start_date,
            "end_date": end_date,
            "class": class_name,
            "division": division_name,
            "weeks_generated": len(timetable_result),
            "timetable": timetable_result
        }

    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}