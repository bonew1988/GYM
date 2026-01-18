from flask import Flask, render_template, request, redirect, abort
import sqlite3
from datetime import datetime

app = Flask(__name__)

WORKOUTS = {
    "A": [
        "Подтягивания",
        "Жим лёжа",
        "Тяга штанги в наклоне",
        "Жим гантелей под углом",
        "Face Pull",
        "Пресс",
        "Планка / боковая планка"
    ],
    "B": [
        "Становая тяга",
        "Болгарские сплит-приседы",
        "Гиперэкстензия",
        "Подтягивания (объём)",
        "Икры",
        "Мостик / ягодичный мост"
    ],
    "C": [
        "Жим штанги стоя",
        "Подтягивания узкие",
        "Разведения в стороны",
        "Тяга к лицу",
        "Бицепс / Трицепс",
        "Пресс / вакуум",
        "Финишер HIIT"
    ]
}


DB_FILE = "database.db"

def get_db():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            day TEXT,
            exercise TEXT,
            weight REAL,
            reps INTEGER
        )
    """)
    con.commit()
    return con

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/workout/<day>", methods=["GET", "POST"])
def workout(day):
    if day not in WORKOUTS:
        abort(404)

    exercises = WORKOUTS[day]
    con = get_db()
    cur = con.cursor()

    if request.method == "POST":
        # --- +1 подход ---
        if request.form.get("quick"):
            cur.execute("""
                SELECT exercise, weight, reps
                FROM logs
                WHERE day=?
                ORDER BY id DESC
                LIMIT 1
            """, (day,))
            last = cur.fetchone()
            if last:
                exercise = last["exercise"]
                weight = last["weight"] or 0
                reps = last["reps"] or 0
                date_iso = datetime.now().strftime("%Y-%m-%d %H:%M")
                cur.execute("""
                    INSERT INTO logs (date, day, exercise, weight, reps)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    date_iso,
                    day,
                    exercise,
                    weight,
                    reps
                ))
                con.commit()
            con.close()
            return redirect(f"/workout/{day}")

        # --- обычное добавление ---
        exercise = request.form["exercise"]
        weight = request.form.get("weight") or 0
        reps = request.form.get("reps") or 0
        date_iso = datetime.now().strftime("%Y-%m-%d %H:%M")

        cur.execute("""
            INSERT INTO logs (date, day, exercise, weight, reps)
            VALUES (?, ?, ?, ?, ?)
        """, (
            date_iso,
            day,
            exercise,
            float(weight),
            int(reps)
        ))
        con.commit()
        con.close()
        return redirect(f"/workout/{day}")

    # Получаем все записи с id
    cur.execute("SELECT id, date, exercise, weight, reps FROM logs WHERE day=? ORDER BY id DESC", (day,))
    logs = cur.fetchall()
    con.close()

    # Определяем последнее выбранное упражнение
    last_exercise = logs[0]['exercise'] if logs else None

    return render_template(
        "workout.html",
        day=day,
        exercises=exercises,
        logs=logs,
        last_exercise=last_exercise
    )

@app.route("/delete/<int:log_id>", methods=["POST"])
def delete_log(log_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT day FROM logs WHERE id=?", (log_id,))
    row = cur.fetchone()
    if not row:
        con.close()
        abort(404)
    day = row["day"]
    cur.execute("DELETE FROM logs WHERE id=?", (log_id,))
    con.commit()
    con.close()
    return redirect(f"/workout/{day}")

@app.route("/graphs")
def all_graphs():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        SELECT day, exercise, date, weight, reps
        FROM logs
        ORDER BY day, exercise, date
    """)
    logs = cur.fetchall()
    con.close()

    data = {}
    for row in logs:
        day = row["day"]
        exercise = row["exercise"]
        date = row["date"]
        weight = row["weight"]
        reps = row["reps"]

        if day not in data:
            data[day] = {}
        if exercise not in data[day]:
            data[day][exercise] = []

        # Используем ISO дату
        data[day][exercise].append({
            "date": date,  # теперь уже ISO YYYY-MM-DD HH:MM
            "weight": weight,
            "reps": reps
        })

    return render_template("graphs.html", data=data)

@app.route("/recommendations")
def recommendations():
    return render_template("recommendations.html")

@app.route("/history")
def history():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT day, exercise, date, weight, reps FROM logs ORDER BY id DESC")
    rows = cur.fetchall()
    con.close()

    # Группируем по дням
    history_data = {}
    for row in rows:
        day = row["day"]
        if day not in history_data:
            history_data[day] = []
        history_data[day].append({
            "exercise": row["exercise"],
            "weight": row["weight"],
            "reps": row["reps"],
            "date": row["date"]
        })

    return render_template("history.html", history=history_data)




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
