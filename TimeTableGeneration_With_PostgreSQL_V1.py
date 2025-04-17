# timetable_generator.py

import psycopg2
from ortools.sat.python import cp_model
import json

# --- PostgreSQL Connection ---
conn = psycopg2.connect(
    dbname="beta_base_db",
    user="psqlsynthadmin",
    password="PSQL$ynth#2024",
    host="base-report-synth-postgredb.cb6ae20mupdy.ap-south-1.rds.amazonaws.com",
    port="5432"
)
cur = conn.cursor()

# --- Fetch Subjects and Teachers ---
cur.execute("""
    SELECT sf.faculty_id, gm.name as subject_name,
           sf.first_name || ' ' || sf.last_name AS faculty_name
    FROM public.subject_faculty sf
    JOIN public.generic_master_data gm ON sf.subject_id = gm.id;
""")
subject_teacher_rows = cur.fetchall()
subject_teacher_map = {}
teacher_subjects_map = {}

for fid, subject, teacher in subject_teacher_rows:
    subject_teacher_map[subject] = teacher
    if teacher not in teacher_subjects_map:
        teacher_subjects_map[teacher] = []
    teacher_subjects_map[teacher].append(subject)

# --- Fetch Class-Division Info ---
cur.execute("""
    SELECT d.id AS division_id, d.name AS division_name,
           c.id AS class_id, c.name AS class_name
    FROM public.generic_master_data d
    JOIN public.generic_master_data c ON d.parent_id = c.id
    WHERE d.master_id = 24 AND c.master_id = 23;
""")
class_division_rows = cur.fetchall()
class_division_map = {}
for division_id, division_name, class_id, class_name in class_division_rows:
    key = f"{class_name}{division_name}"
    class_division_map[key] = {
        'class_id': class_id,
        'division_id': division_id
    }

# --- Fetch Classrooms ---
cur.execute("SELECT id, name FROM public.generic_master_data WHERE master_id = 22;")
classroom_rows = cur.fetchall()
classroom_dict = {row[0]: row[1] for row in classroom_rows}

# --- Fetch Division-Classroom Mapping ---
cur.execute("""
    SELECT d.id AS division_id, d.name AS division_name,
           c.id AS class_id, c.name AS class_name
    FROM public.generic_master_data d
    JOIN public.generic_master_data c
      ON d.parent_id = c.id
    WHERE d.master_id = 24 AND c.master_id = 23;
""")
division_classroom_rows = cur.fetchall()
# division_classroom_map = {div_id: room_id for div_id, room_id in division_classroom_rows}
division_classroom_map = {row[0]: None for row in division_classroom_rows}

# Merge classroom into class_division_map
for key, val in class_division_map.items():
    division_id = val["division_id"]
    classroom_id = division_classroom_map.get(division_id)
    val["classroom_id"] = classroom_id
    val["classroom_name"] = classroom_dict.get(classroom_id)

# --- Timetable CSP Setup ---
days = range(5)
periods_per_day = 4
subjects = list(subject_teacher_map.keys())
classes = list(class_division_map.keys())

model = cp_model.CpModel()
timetable_vars = {}

for cls in classes:
    for d in days:
        for p in range(periods_per_day):
            for subj in subjects:
                var = model.NewBoolVar(f"{cls}_{d}_{p}_{subj}")
                timetable_vars[(cls, d, p, subj)] = var

# Constraints: One subject per period per class
timetable_output = {}
for cls in classes:
    timetable_output[cls] = {}
    for d in days:
        timetable_output[cls][f"Day {d+1}"] = ["---"] * periods_per_day
        for p in range(periods_per_day):
            model.AddExactlyOne([timetable_vars[(cls, d, p, subj)] for subj in subjects])

# Subject allocation limit (e.g., 5 times per week)
for cls in classes:
    for subj in subjects:
        model.Add(sum(
            timetable_vars[(cls, d, p, subj)]
            for d in days for p in range(periods_per_day)
        ) <= 5)

# to prevent a subject from being scheduled more than 2 times in a day
for cls in classes:
    for d in days:
        for subj in subjects:
            model.Add(
                sum(timetable_vars[(cls, d, p, subj)] for p in range(periods_per_day)) <= 2
            )

# Distribute Subjects Across Week
for cls in classes:
    for subj in subjects:
        # Subject must appear on at least 2 different days
        appear_on_day = []
        for d in days:
            appear = model.NewBoolVar(f"{cls}_{subj}_appears_on_day_{d}")
            model.AddMaxEquality(
                appear,
                [timetable_vars[(cls, d, p, subj)] for p in range(periods_per_day)]
            )
            appear_on_day.append(appear)
        model.Add(sum(appear_on_day) >= 2)

# Avoid Back-to-Back Same Subjects
for cls in classes:
    for d in days:
        for p in range(periods_per_day - 1):
            for subj in subjects:
                model.AddBoolOr([
                    timetable_vars[(cls, d, p, subj)].Not(),
                    timetable_vars[(cls, d, p+1, subj)].Not()
                ])

# --- Solve Model ---
solver = cp_model.CpSolver()
status = solver.Solve(model)

if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
    for cls in classes:
        for d in days:
            for p in range(periods_per_day):
                for subj in subjects:
                    if solver.Value(timetable_vars[(cls, d, p, subj)]):
                        timetable_output[cls][f"Day {d+1}"][p] = subj

    # Output JSON
    json_output = json.dumps(timetable_output, indent=4)
    print("\n✅ Timetable JSON Output:\n")
    print(json_output)
else:
    print("❌ No feasible timetable found.")

# Close DB connection
cur.close()
conn.close()
