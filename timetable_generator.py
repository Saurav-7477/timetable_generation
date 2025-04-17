# # import psycopg2
# # from ortools.sat.python import cp_model
# # import json

# # def get_divisions_for_class(class_name: str):
# #     conn = psycopg2.connect(
# #         dbname="beta_base_db",
# #         user="psqlsynthadmin",
# #         password="PSQL$ynth#2024",
# #         host="base-report-synth-postgredb.cb6ae20mupdy.ap-south-1.rds.amazonaws.com",
# #         port="5432"
# #     )
# #     cur = conn.cursor()
    
# #     query = """
# #     SELECT c.name AS class_name, d.name AS division_name
# #     FROM generic_master_data d
# #     JOIN generic_master_data c ON d.parent_id = c.id
# #     WHERE c.master_id = 23 AND d.master_id = 24 AND c.name = %s
# #     """
# #     cur.execute(query, (class_name,))
# #     rows = cur.fetchall()
# #     cur.close()
# #     conn.close()

# #     return [f"{row[0]}  Div - {row[1]}" for row in rows]

# # def timetable_generator(days: list[int], class_div_key: str):
# #     # --- PostgreSQL Connection ---
# #     conn = psycopg2.connect(
# #         dbname="beta_base_db",
# #         user="psqlsynthadmin",
# #         password="PSQL$ynth#2024",
# #         host="base-report-synth-postgredb.cb6ae20mupdy.ap-south-1.rds.amazonaws.com",
# #         port="5432"
# #     )
# #     cur = conn.cursor()

# #     # --- Fetch Subjects and Teachers ---
# #     cur.execute("""
# #         SELECT sf.faculty_id, gm.name as subject_name,
# #                sf.first_name || ' ' || sf.last_name AS faculty_name
# #         FROM public.subject_faculty sf
# #         JOIN public.generic_master_data gm ON sf.subject_id = gm.id;
# #     """)
# #     subject_teacher_rows = cur.fetchall()
# #     subject_teacher_map = {}

# #     for faculty_id, subject_name, teacher_name in subject_teacher_rows:
# #         if subject_name not in subject_teacher_map:
# #             subject_teacher_map[subject_name] = []
# #         subject_teacher_map[subject_name].append({
# #             'faculty_id': faculty_id,
# #             'teacher_name': teacher_name
# #         })

# #     # --- Fetch Class-Division Info ---
# #     cur.execute("""
# #         SELECT d.id AS division_id, d.name AS division_name,
# #                c.id AS class_id, c.name AS class_name
# #         FROM public.generic_master_data d
# #         JOIN public.generic_master_data c ON d.parent_id = c.id
# #         WHERE d.master_id = 24 AND c.master_id = 23;
# #     """)
# #     class_division_rows = cur.fetchall()
# #     class_division_map = {}
# #     for division_id, division_name, class_id, class_name in class_division_rows:
# #         key = f"{class_name} {division_name}"
# #         class_division_map[key] = {
# #             'class_id': class_id,
# #             'division_id': division_id
# #         }

# #     # --- Fetch Classrooms ---
# #     cur.execute("SELECT id, name FROM public.generic_master_data WHERE master_id = 22;")
# #     classroom_rows = cur.fetchall()
# #     classroom_dict = {row[0]: row[1] for row in classroom_rows}

# #     # --- Fetch Division-Classroom Mapping (set to None if missing) ---
# #     cur.execute("""
# #     SELECT d.id AS division_id, d.name AS division_name,
# #            c.id AS class_id, c.name AS class_name
# #     FROM public.generic_master_data d
# #     JOIN public.generic_master_data c
# #       ON d.parent_id = c.id
# #     WHERE d.master_id = 24 AND c.master_id = 23;
# #         """)

# #     division_classroom_rows = cur.fetchall()
# #     division_classroom_map = {row[0]: row[1] for row in division_classroom_rows}

# #     # Merge classroom info into class_division_map
# #     for key, val in class_division_map.items():
# #         division_id = val["division_id"]
# #         classroom_id = division_classroom_map.get(division_id)
# #         val["classroom_id"] = classroom_id
# #         val["classroom_name"] = classroom_dict.get(classroom_id, "Unknown")

# #     # --- Validate class_div_key ---
# #     if class_div_key not in class_division_map:
# #         cur.close()
# #         conn.close()
# #         return {"error": f"Invalid class-division: '{class_div_key}' not found."}

# #     # --- Timetable Setup ---
# #     periods_per_day = 4
# #     subjects = list(subject_teacher_map.keys())
# #     classes = [class_div_key]  # Only the one requested class-div

# #     model = cp_model.CpModel()
# #     timetable_vars = {}

# #     for cls in classes:
# #         for d in days:
# #             for p in range(periods_per_day):
# #                 for subj in subjects:
# #                     var = model.NewBoolVar(f"{cls}_{d}_{p}_{subj}")
# #                     timetable_vars[(cls, d, p, subj)] = var

# #     # --- Constraints ---
# #     for cls in classes:
# #         for d in days:
# #             for p in range(periods_per_day):
# #                 model.AddExactlyOne([timetable_vars[(cls, d, p, subj)] for subj in subjects])

# #     for cls in classes:
# #         for subj in subjects:
# #             model.Add(sum(
# #                 timetable_vars[(cls, d, p, subj)]
# #                 for d in days for p in range(periods_per_day)
# #             ) <= 5)

# #     # --- Solve Model ---
# #     solver = cp_model.CpSolver()
# #     status = solver.Solve(model)

# #     # --- Generate Output ---
# #     if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
# #         timetable_output = {}
# #         cls = classes[0]
# #         timetable_output[cls] = {}
# #         classroom = class_division_map[cls]['classroom_name']

# #         for d in days:
# #             day_key = f"Day {d + 1}"
# #             timetable_output[cls][day_key] = []
# #             for p in range(periods_per_day):
# #                 assigned_subj = None
# #                 for subj in subjects:
# #                     if solver.Value(timetable_vars[(cls, d, p, subj)]):
# #                         assigned_subj = subj
# #                         break
# #                 if assigned_subj:
# #                     teacher = subject_teacher_map[assigned_subj][0]['teacher_name']
# #                     timetable_output[cls][day_key].append({
# #                         'period': p + 1,
# #                         'subject': assigned_subj,
# #                         'teacher': teacher,
# #                         'room': classroom
# #                     })
# #                 else:
# #                     timetable_output[cls][day_key].append({
# #                         'period': p + 1,
# #                         'subject': "---",
# #                         'teacher': "---",
# #                         'room': classroom
# #                     })

# #         cur.close()
# #         conn.close()
# #         return timetable_output
# #     else:
# #         cur.close()
# #         conn.close()
# #         return {"error": "No feasible timetable found."}



# import psycopg2
# from ortools.sat.python import cp_model
# import json
# from datetime import datetime, timedelta

# # Helper to fetch all class-division keys for a given class name (e.g., "8th")
# def get_divisions_for_class(class_name: str):
#     conn = psycopg2.connect(
#         dbname="beta_base_db",
#         user="psqlsynthadmin",
#         password="PSQL$ynth#2024",
#         host="base-report-synth-postgredb.cb6ae20mupdy.ap-south-1.rds.amazonaws.com",
#         port="5432"
#     )
#     cur = conn.cursor()

#     query = """
#     SELECT c.name AS class_name, d.name AS division_name
#     FROM generic_master_data d
#     JOIN generic_master_data c ON d.parent_id = c.id
#     WHERE c.master_id = 5 AND d.master_id = 24 AND c.name = %s
#     """
#     cur.execute(query, (class_name,))
#     rows = cur.fetchall()
#     cur.close()
#     conn.close()

#     return [f"{row[0]}  Div - {row[1]}" for row in rows]

# def get_weekdays_in_range(start_date: str, end_date: str):
#     """Returns list of (date, weekday) tuples for weekdays (Mon-Fri) in the given range."""
#     start = datetime.strptime(start_date, "%Y-%m-%d")
#     end = datetime.strptime(end_date, "%Y-%m-%d")

#     delta = end - start
#     weekdays = []

#     for i in range(delta.days + 1):
#         current_date = start + timedelta(days=i)
#         if current_date.weekday() < 5:  # 0=Monday, 4=Friday
#             weekdays.append((current_date.date(), current_date.strftime("%A")))

#     return weekdays

# # Main timetable generation function
# def timetable_generator(days: list[int], class_div_keys: list[str]):
#     # --- PostgreSQL Connection ---
#     conn = psycopg2.connect(
#         dbname="beta_base_db",
#         user="psqlsynthadmin",
#         password="PSQL$ynth#2024",
#         host="base-report-synth-postgredb.cb6ae20mupdy.ap-south-1.rds.amazonaws.com",
#         port="5432"
#     )
#     cur = conn.cursor()

#     # --- Fetch Subjects and Teachers ---
#     cur.execute("""
#         SELECT sf.faculty_id, gm.name as subject_name,
#                sf.first_name || ' ' || sf.last_name AS faculty_name
#         FROM public.subject_faculty sf
#         JOIN public.generic_master_data gm ON sf.subject_id = gm.id;
#     """)
#     subject_teacher_rows = cur.fetchall()
#     subject_teacher_map = {}
#     teacher_subject_map = {}

#     for faculty_id, subject_name, teacher_name in subject_teacher_rows:
#         if subject_name not in subject_teacher_map:
#             subject_teacher_map[subject_name] = []
#         subject_teacher_map[subject_name].append({
#             'faculty_id': faculty_id,
#             'teacher_name': teacher_name
#         })
#         if teacher_name not in teacher_subject_map:
#             teacher_subject_map[teacher_name] = []
#         teacher_subject_map[teacher_name].append(subject_name)

#     # --- Fetch Class-Division Info ---
#     cur.execute("""
#         SELECT d.id AS division_id, d.name AS division_name,
#                c.id AS class_id, c.name AS class_name
#         FROM public.generic_master_data d
#         JOIN public.generic_master_data c ON d.parent_id = c.id
#         WHERE d.master_id = 24 AND c.master_id = 5;
#     """)
#     class_division_rows = cur.fetchall()
#     class_division_map = {}
#     for division_id, division_name, class_id, class_name in class_division_rows:
#         key = f"{class_name}  Div - {division_name}"
#         class_division_map[key] = {
#             'class_id': class_id,
#             'division_id': division_id
#         }

#     # --- Fetch Classrooms ---
#     cur.execute("SELECT id, name FROM public.generic_master_data WHERE master_id = 22;")
#     classroom_rows = cur.fetchall()
#     classroom_dict = {row[0]: row[1] for row in classroom_rows}

#     # --- Fetch Division-Classroom Mapping ---
#     # cur.execute("SELECT division_id, classroom_id FROM class_room_master;")
#     # division_classroom_rows = cur.fetchall()
#     # division_classroom_map = {div_id: room_id for div_id, room_id in division_classroom_rows}

#     # Merge classroom into class_division_map
#     for key, val in class_division_map.items():
#         division_id = val["division_id"]
#         classroom_id = class_division_map.get(division_id)
#         val["classroom_id"] = classroom_id
#         val["classroom_name"] = classroom_dict.get(classroom_id, "Unknown")

#     # --- Timetable Setup ---
#     periods_per_day = 5
#     subjects = list(subject_teacher_map.keys())
#     classes = [key for key in class_div_keys if key in class_division_map]

#     model = cp_model.CpModel()
#     timetable_vars = {}

#     for cls in classes:
#         for d in days:
#             for p in range(periods_per_day):
#                 for subj in subjects:
#                     var = model.NewBoolVar(f"{cls}_{d}_{p}_{subj}")
#                     timetable_vars[(cls, d, p, subj)] = var

#     # --- Constraints ---
#     for cls in classes:
#         for d in days:
#             for p in range(periods_per_day):
#                 model.AddExactlyOne([timetable_vars[(cls, d, p, subj)] for subj in subjects])

#     for cls in classes:
#         for subj in subjects:
#             model.Add(sum(
#                 timetable_vars[(cls, d, p, subj)]
#                 for d in days for p in range(periods_per_day)
#             ) <= 5)

#     # --- Solve Model ---
#     solver = cp_model.CpSolver()
#     status = solver.Solve(model)

#     # --- Generate Output ---
#     if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
#         timetable_output = {}

#         for cls in classes:
#             timetable_output[cls] = {}
#             classroom = class_division_map[cls]['classroom_name']
#             for d in days:
#                 day_key = f"Day {d + 1}"
#                 timetable_output[cls][day_key] = []
#                 for p in range(periods_per_day):
#                     assigned_subj = None
#                     for subj in subjects:
#                         if solver.Value(timetable_vars[(cls, d, p, subj)]):
#                             assigned_subj = subj
#                             break
#                     if assigned_subj:
#                         teacher = subject_teacher_map[assigned_subj][0]['teacher_name']
#                         timetable_output[cls][day_key].append({
#                             'period': p + 1,
#                             'subject': assigned_subj,
#                             'teacher': teacher,
#                             'room': classroom
#                         })
#                     else:
#                         timetable_output[cls][day_key].append({
#                             'period': p + 1,
#                             'subject': "---",
#                             'teacher': "---",
#                             'room': classroom
#                         })

#         cur.close()
#         conn.close()
#         return timetable_output

#     else:
#         cur.close()
#         conn.close()
#         return {"error": "No feasible timetable found."}



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

    # Merge classroom info
    for key, val in class_division_map.items():
        division_id = val["division_id"]
        classroom_id = class_division_map.get(division_id)
        val["classroom_id"] = classroom_id
        val["classroom_name"] = classroom_dict.get(classroom_id, "Unknown")

    # --- Determine class_div_keys based on input ---
    if class_name:
        class_div_keys = [key for key in class_division_map.keys() if key.startswith(class_name)]

    if not class_div_keys:
        return {"error": "No class/division keys provided or found."}

    working_days = get_working_days(start_date, end_date)
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

    # --- Constraints ---
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

    # --- Solve Model ---
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # --- Generate Output ---
    if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
        timetable_output = {}

        for cls in classes:
            timetable_output[cls] = {}
            classroom = class_division_map[cls]['classroom_name']

            for i, work_day in enumerate(working_days):
                weekday_name = work_day.strftime("%A")
                date_str = work_day.strftime("%Y-%m-%d")
                label = f"{weekday_name} ({date_str})"
                timetable_output[cls][label] = []

                for p in range(periods_per_day):
                    assigned_subj = None
                    for subj in subjects:
                        if solver.Value(timetable_vars[(cls, i, p, subj)]):
                            assigned_subj = subj
                            break
                    if assigned_subj:
                        teacher = subject_teacher_map[assigned_subj][0]['teacher_name']
                        timetable_output[cls][label].append({
                            'period': p + 1,
                            'subject': assigned_subj,
                            'teacher': teacher,
                            'room': classroom
                        })
                    else:
                        timetable_output[cls][label].append({
                            'period': p + 1,
                            'subject': "---",
                            'teacher': "---",
                            'room': classroom
                        })

        cur.close()
        conn.close()
        return timetable_output
    else:
        cur.close()
        conn.close()
        return {"error": "No feasible timetable found."}
