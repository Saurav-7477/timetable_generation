from ortools.sat.python import cp_model
from collections import defaultdict
import json

# ======= Sample Data =======

classes = ['6A', '6B']
subjects = ['English', 'Math', 'Science', 'Marathi', 'History']
teachers = ['Ms. Khan', 'Mr. Patel', 'Ms. Rani', 'Mr. Patil', 'Ms. Pooja']

teacher_to_subjects = {
    'Ms. Khan': ['English'],
    'Mr. Patel': ['Math'],
    'Ms. Rani': ['Science'],
    'Mr. Patil': ['Marathi'],
    'Ms. Pooja': ['History', 'Marathi']
}

# Inverse map: subject -> teachers
subject_to_teachers = defaultdict(list)
for teacher, subj_list in teacher_to_subjects.items():
    for subj in subj_list:
        subject_to_teachers[subj].append(teacher)

# Classrooms
classrooms = ['Room A', 'Room B']

# Days and periods
days = range(5)     # 0-4 = Mon-Fri
periods = range(4)  # 4 periods/day

# Simulated holidays from DB (day index starts from 0)
blocked_days = {
    '6A': [1],  # Tuesday off
    '6B': [3]   # Thursday off
}

# ======= CP-SAT Model =======

model = cp_model.CpModel()

timetable_vars = {}
classroom_vars = {}

# Define timetable variables
for cls in classes:
    for d in days:
        if d in blocked_days.get(cls, []):
            continue
        for p in periods:
            for subj in subjects:
                for teacher in subject_to_teachers[subj]:
                    timetable_vars[(cls, d, p, subj, teacher)] = model.NewBoolVar(f"{cls}_d{d}_p{p}_{subj}_{teacher}")
            for room in classrooms:
                classroom_vars[(cls, d, p, room)] = model.NewBoolVar(f"{cls}_d{d}_p{p}_{room}")

# One subject-teacher per slot
for cls in classes:
    for d in days:
        if d in blocked_days.get(cls, []):
            continue
        for p in periods:
            model.AddExactlyOne(
                timetable_vars[(cls, d, p, subj, teacher)]
                for subj in subjects
                for teacher in subject_to_teachers[subj]
            )
            model.AddExactlyOne(
                classroom_vars[(cls, d, p, room)]
                for room in classrooms
            )

# No teacher conflict (only one slot per time)
for teacher in teachers:
    for d in days:
        for p in periods:
            teacher_slots = []
            for cls in classes:
                if d in blocked_days.get(cls, []):
                    continue
                for subj in teacher_to_subjects.get(teacher, []):
                    key = (cls, d, p, subj, teacher)
                    if key in timetable_vars:
                        teacher_slots.append(timetable_vars[key])
            model.AddAtMostOne(teacher_slots)

# No room conflict
for room in classrooms:
    for d in days:
        for p in periods:
            room_slots = []
            for cls in classes:
                if d in blocked_days.get(cls, []):
                    continue
                key = (cls, d, p, room)
                if key in classroom_vars:
                    room_slots.append(classroom_vars[key])
            model.AddAtMostOne(room_slots)

# ======= Solve Model =======

solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 10.0
status = solver.Solve(model)

# ======= Output as JSON =======

if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
    timetable_json = defaultdict(lambda: defaultdict(list))

    for cls in classes:
        for d in days:
            day_key = f'Day {d+1}'
            if d in blocked_days.get(cls, []):
                timetable_json[cls][day_key] = "Holiday"
                continue

            for p in periods:
                entry = {
                    "period": p + 1,
                    "subject": "---",
                    "teacher": None,
                    "room": None
                }

                for subj in subjects:
                    for teacher in subject_to_teachers[subj]:
                        key = (cls, d, p, subj, teacher)
                        if key in timetable_vars and solver.Value(timetable_vars[key]):
                            entry["subject"] = subj
                            entry["teacher"] = teacher

                for room in classrooms:
                    room_key = (cls, d, p, room)
                    if room_key in classroom_vars and solver.Value(classroom_vars[room_key]):
                        entry["room"] = room

                timetable_json[cls][day_key].append(entry)

    # Pretty print
    print(json.dumps(timetable_json, indent=4))

else:
    print("❌ No feasible timetable found.")
