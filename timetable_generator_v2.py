import psycopg2
from ortools.sat.python import cp_model
from datetime import datetime, timedelta


def get_working_days(start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    current = start_date
    working_days = []

    while current <= end_date:
        if current.weekday() < 5:  # Monday=0, Friday=4
            working_days.append(current)
        current += timedelta(days=1)

    return working_days


def timetable_generator(start_date: str, end_date: str, class_name: str = None, class_div_keys: list[str] = None):
    conn = psycopg2.connect(
        dbname="beta_base_db",
        user="psqlsynthadmin",
        password="PSQL$ynth#2024",
        host="base-report-synth-postgredb.cb6ae20mupdy.ap-south-1.rds.amazonaws.com",
        port="5432"
    )
    cur = conn.cursor()

    # Fetch already existing dates from ai_timetable
    cur.execute("SELECT DISTINCT date FROM public.ai_timetable;")
    existing_dates = set(row[0] for row in cur.fetchall())

    # --- Fetch Subjects and Teachers ---
    cur.execute("""
        SELECT sf.faculty_id, gm.name as subject_name,
               sf.first_name || ' ' || sf.last_name AS faculty_name
        FROM public.subject_faculty sf
        JOIN public.generic_master_data gm ON sf.subject_id = gm.id;
    """)
    subject_teacher_rows = cur.fetchall()
    subject_teacher_map = {}
    teacher_subject_map = {}

    for faculty_id, subject_name, teacher_name in subject_teacher_rows:
        if subject_name not in subject_teacher_map:
            subject_teacher_map[subject_name] = []
        subject_teacher_map[subject_name].append({
            'faculty_id': faculty_id,
            'teacher_name': teacher_name
        })
        if teacher_name not in teacher_subject_map:
            teacher_subject_map[teacher_name] = []
        teacher_subject_map[teacher_name].append(subject_name)

    # --- Fetch Class-Division Info ---
    cur.execute("""
        SELECT d.id AS division_id, d.name AS division_name,
               c.id AS class_id, c.name AS class_name
        FROM public.generic_master_data d
        JOIN public.generic_master_data c ON d.parent_id = c.id
        WHERE d.master_id = 24 AND c.master_id = 5;
    """)
    class_division_rows = cur.fetchall()
    class_division_map = {}
    for division_id, division_name, class_id, cls_name in class_division_rows:
        key = f"{cls_name}  Div - {division_name}"
        class_division_map[key] = {
            'class_id': class_id,
            'division_id': division_id,
            'class_name': cls_name,
            'division_name': division_name
        }

    # --- Fetch Classrooms ---
    cur.execute("SELECT id, name FROM public.generic_master_data WHERE master_id = 22;")
    classroom_rows = cur.fetchall()
    classroom_dict = {row[0]: row[1] for row in classroom_rows}

    # Merge classroom info (placeholder mapping if no direct assignment)
    for key, val in class_division_map.items():
        val["classroom_id"] = None
        val["classroom_name"] = classroom_dict.get(val["division_id"], "Unknown")

    if class_name:
        class_div_keys = [key for key in class_division_map.keys() if key.startswith(class_name)]

    if not class_div_keys:
        return {"error": "No class/division keys provided or found."}

    all_working_days = get_working_days(start_date, end_date)
    working_days = [d for d in all_working_days if d.date() not in existing_dates]

    if not working_days:
        return {"message": "No new working days to generate timetable."}

    subjects = list(subject_teacher_map.keys())
    periods_per_day = 4
    classes = [key for key in class_div_keys if key in class_division_map]

    model = cp_model.CpModel()
    timetable_vars = {}

    for cls in classes:
        for day_index in range(len(working_days)):
            for p in range(periods_per_day):
                for subj in subjects:
                    var = model.NewBoolVar(f"{cls}_{day_index}_{p}_{subj}")
                    timetable_vars[(cls, day_index, p, subj)] = var

    # Constraints
    for cls in classes:
        for day_index in range(len(working_days)):
            for p in range(periods_per_day):
                model.AddExactlyOne([timetable_vars[(cls, day_index, p, subj)] for subj in subjects])

    for cls in classes:
        for subj in subjects:
            model.Add(sum(
                timetable_vars[(cls, d, p, subj)]
                for d in range(len(working_days)) for p in range(periods_per_day)
            ) <= 5)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
        insert_data = []

        for cls in classes:
            classroom = class_division_map[cls]['classroom_name']
            class_name = class_division_map[cls]['class_name']
            division_name = class_division_map[cls]['division_name']

            for i, work_day in enumerate(working_days):
                weekday_name = work_day.strftime("%A")
                date_val = work_day.date()

                for p in range(periods_per_day):
                    assigned_subj = None
                    for subj in subjects:
                        if solver.Value(timetable_vars[(cls, i, p, subj)]):
                            assigned_subj = subj
                            break
                    if assigned_subj:
                        teacher = subject_teacher_map[assigned_subj][0]['teacher_name']
                    else:
                        teacher = "---"
                        assigned_subj = "---"

                    insert_data.append((
                        class_name,
                        classroom,
                        date_val,
                        weekday_name,
                        division_name,
                        p + 1,
                        assigned_subj,
                        teacher
                    ))

        # Insert into ai_timetable
        insert_query = """
    INSERT INTO public.ai_timetable
    (class_name, classroom, date, day_of_week, division_name, period_number, subject, teacher)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""
        cur.executemany(insert_query, insert_data)
        conn.commit()

        cur.close()
        conn.close()
        return {"message": f"Timetable successfully generated and stored for {len(working_days)} new days."}
    else:
        cur.close()
        conn.close()
        return {"error": "No feasible timetable found."}
