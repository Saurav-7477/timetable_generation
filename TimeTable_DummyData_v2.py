from ortools.sat.python import cp_model
from collections import defaultdict
import json


classes = ['6A', '6B']
subjects = ['English', 'Math', 'Science', 'Marathi', 'History']
days = range(5)     # Monday to Friday
periods = range(4)  # 4 periods per day

teacher_to_subjects = {
    'Ms. Khan': ['English'],
    'Mr. Patel': ['Math'],
    'Ms. Rani': ['Science'],
    'Mr. Patil': ['Marathi'],
    'Ms. Pooja': ['History', 'Marathi']
}

# Create reverse mapping: subject → eligible teachers
subject_to_teachers = defaultdict(list)
for teacher, subj_list in teacher_to_subjects.items():
    for subj in subj_list:
        subject_to_teachers[subj].append(teacher)

# ======= CP-SAT Model =======

model = cp_model.CpModel()

# Create decision variables
# Key: (class, day, period, subject, teacher)
timetable_vars = {}
for cls in classes:
    for d in days:
        for p in periods:
            for subj in subjects:
                for teacher in subject_to_teachers[subj]:
                    timetable_vars[(cls, d, p, subj, teacher)] = model.NewBoolVar(
                        f"{cls}_d{d}_p{p}_{subj}_{teacher}"
                    )

# Constraint 1: Each slot gets exactly one subject-teacher pair
for cls in classes:
    for d in days:
        for p in periods:
            model.AddExactlyOne(
                timetable_vars[(cls, d, p, subj, teacher)]
                for subj in subjects
                for teacher in subject_to_teachers[subj]
            )

# Constraint 2: A teacher can't be in more than one place at the same time
for teacher in teacher_to_subjects:
    for d in days:
        for p in periods:
            model.AddAtMostOne(
                timetable_vars[(cls, d, p, subj, teacher)]
                for cls in classes
                for subj in teacher_to_subjects[teacher]
                if (cls, d, p, subj, teacher) in timetable_vars
            )

# ======= Solve Model =======

solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 10.0
status = solver.Solve(model)

# ======= Output as JSON =======

if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
    timetable_json = defaultdict(lambda: defaultdict(list))

    for cls in classes:
        for d in days:
            day_key = f"Day {d+1}"
            for p in periods:
                slot_found = False
                for subj in subjects:
                    for teacher in subject_to_teachers[subj]:
                        key = (cls, d, p, subj, teacher)
                        if key in timetable_vars and solver.Value(timetable_vars[key]) == 1:
                            timetable_json[cls][day_key].append({
                                "period": p + 1,
                                "subject": subj,
                                "teacher": teacher
                            })
                            slot_found = True
                            break
                    if slot_found:
                        break
                if not slot_found:
                    timetable_json[cls][day_key].append({
                        "period": p + 1,
                        "subject": "---",
                        "teacher": None
                    })

    # Print nicely formatted JSON
    print(json.dumps(timetable_json, indent=4))
else:
    print("❌ No feasible timetable found.")
