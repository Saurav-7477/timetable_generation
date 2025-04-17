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
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if start > end:
            return {"error": "start_date must be earlier than end_date"}

        current = start
        weekly_outputs = {}
        week_num = 1

        while current <= end:
            weekdays = []
            temp = current
            while len(weekdays) < 5 and temp <= end:
                if temp.weekday() < 5:
                    weekdays.append(temp)
                temp += timedelta(days=1)

            if weekdays:
                day_indices = [d.weekday() for d in weekdays]
                timetable = timetable_generator(days=day_indices)
                weekly_outputs[f"Week {week_num}"] = {
                    "dates": [d.strftime("%Y-%m-%d") for d in weekdays],
                    "timetable": timetable
                }
                week_num += 1
                current = temp
            else:
                current += timedelta(days=1)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "weeks_generated": len(weekly_outputs),
            "weekly_timetables": weekly_outputs
        }

    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}