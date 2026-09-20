import flet as ft
import csv
import os
import traceback
from datetime import datetime, timedelta

# --- 1. 로컬 데이터 스토리지 구성 (CSV) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = {
    "food_database": os.path.join(BASE_DIR, "food_database.csv"),
    "user_goal": os.path.join(BASE_DIR, "user_goal.csv"),
    "activity_log": os.path.join(BASE_DIR, "activity_log.csv"),
    "meal_log": os.path.join(BASE_DIR, "meal_log.csv")
}

def init_files():
    if not os.path.exists(FILES["food_database"]):
        with open(FILES["food_database"], 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["food_name", "calories_per_100g", "protein_per_100g"])
            writer.writerows([["닭가슴살", 165, 31], ["쌀밥", 130, 2.7], ["사과", 52, 0.3]]) 

    if not os.path.exists(FILES["user_goal"]):
        with open(FILES["user_goal"], 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["target_calories", "target_steps"])
            writer.writerow([2000, 10000])

    for file_key in ["activity_log", "meal_log"]:
        if not os.path.exists(FILES[file_key]):
            with open(FILES[file_key], 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if file_key == "activity_log":
                    writer.writerow(["date", "walked_steps", "burned_calories"])
                else:
                    writer.writerow(["date", "food_name", "amount_g", "calories", "protein"])

# --- 2. 비즈니스 로직 ---
def get_food_info(food_name):
    try:
        with open(FILES["food_database"], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['food_name'] == food_name:
                    return float(row['calories_per_100g']), float(row['protein_per_100g'])
    except OSError:
        pass 
    return None, None

def calculate_daily_summary(target_date_str):
    total_in_cal, total_protein = 0.0, 0.0
    total_steps, burned_cal = 0, 0.0
    target_cal = 2000

    with open(FILES["user_goal"], 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            target_cal = float(row.get('target_calories', 2000))
            break

    with open(FILES["meal_log"], 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['date'] == target_date_str:
                total_in_cal += float(row['calories'])
                total_protein += float(row['protein'])

    with open(FILES["activity_log"], 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['date'] == target_date_str:
                total_steps += int(row['walked_steps'])
                burned_cal += float(row['burned_calories'])

    net_calories = max(0, total_in_cal - burned_cal)
    achievement_rate = (net_calories / target_cal) * 100 if target_cal > 0 else 0

    return {
        "in_cal": total_in_cal, "protein": total_protein,
        "steps": total_steps, "burned_cal": burned_cal,
        "net_cal": net_calories, "rate": achievement_rate,
        "target_cal": target_cal # UI에 목표량을 보여주기 위해 추가 반환
    }

# --- 3. GUI 화면 및 이벤트 ---
def main(page: ft.Page):
    try:
        page.title = "핏 트래커 (FitTracker)"
        page.window_width = 450
        page.window_height = 700 # 목표 버튼이 추가되어 창 높이를 살짝 늘렸습니다.
        init_files()

        app_state = {"current_date": datetime.now()}

        def get_current_date_str():
            return app_state["current_date"].strftime("%Y-%m-%d")

        date_text = ft.Text(value=get_current_date_str(), size=22, weight="bold")
        summary_text = ft.Text(size=16, weight="bold")
        progress_bar = ft.ProgressBar(width=300, height=20, value=0)
        rate_text = ft.Text(size=20, weight="bold")
        warning_text = ft.Text(color="red", visible=False)

        food_input = ft.TextField(label="음식명 (예: 닭가슴살)", width=150)
        amount_input = ft.TextField(label="섭취량(g)", width=100)
        steps_input = ft.TextField(label="당일 걸음 수", width=150)

        # 달력 위젯 (DatePicker) 설정
        def on_date_selected(e):
            if date_picker.value:
                app_state["current_date"] = date_picker.value
                update_ui()
                
        date_picker = ft.DatePicker(
            on_change=on_date_selected,
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31)
        )
        page.overlay.append(date_picker)

        def open_date_picker(e):
            date_picker.open = True
            page.update()

        def update_ui():
            current_date_str = get_current_date_str()
            date_text.value = current_date_str
            
            summary = calculate_daily_summary(current_date_str)
            
            summary_text.value = (
                f"- 섭취 열량: {summary['in_cal']:.1f} kcal / 단백질: {summary['protein']:.1f} g\n"
                f"- 소비 열량: {summary['burned_cal']:.1f} kcal (걸음 수: {summary['steps']}보)\n"
                f"★ 일일 목표: {summary['target_cal']:.0f} kcal"
            )
            
            rate = summary['rate']
            rate_text.value = f"{rate:.1f}%"
            
            progress_bar.value = max(0.0, min(rate / 100.0, 1.0)) 

            if rate < 80 or rate >= 120:
                progress_bar.color = "red"
                rate_text.color = "red"
                warning_text.value = "안내: 금일 목표 열량에 미달/초과 하였습니다"
                warning_text.visible = True
            else:
                progress_bar.color = "blue"
                rate_text.color = "black"
                warning_text.visible = False

            page.update()

        def change_date(e, delta_days):
            app_state["current_date"] += timedelta(days=delta_days)
            update_ui()

        def show_snack_bar(message):
            snack = ft.SnackBar(ft.Text(message))
            page.overlay.append(snack)
            snack.open = True
            page.update()

        # --- [신규 기능] 목표 수정 팝업 관련 로직 ---
        goal_cal_input = ft.TextField(label="목표 섭취 열량(kcal)", width=200)
        goal_steps_input = ft.TextField(label="목표 걸음 수", width=200)

        def open_goal_settings(e):
            # 현재 저장된 목표치를 불러와서 텍스트 필드에 기본값으로 세팅
            current_cal, current_steps = 2000, 10000
            with open(FILES["user_goal"], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    current_cal = float(row.get('target_calories', 2000))
                    current_steps = int(row.get('target_steps', 10000))
                    break
            goal_cal_input.value = str(current_cal)
            goal_steps_input.value = str(current_steps)
            
            goal_dialog.open = True
            page.update()

        def close_goal_settings(e):
            goal_dialog.open = False
            page.update()

        def save_goals(e):
            try:
                new_cal = float(goal_cal_input.value)
                new_steps = int(goal_steps_input.value)
                if new_cal <= 0 or new_steps <= 0: raise ValueError
            except ValueError:
                show_snack_bar("올바른 양수(숫자)를 입력해주세요.")
                return
            
            # 새 목표치를 CSV에 덮어쓰기
            with open(FILES["user_goal"], 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["target_calories", "target_steps"])
                writer.writerow([new_cal, new_steps])
            
            goal_dialog.open = False
            update_ui()
            show_snack_bar("목표가 성공적으로 수정되었습니다.")

        goal_dialog = ft.AlertDialog(
            title=ft.Text("일일 목표 설정", weight="bold"),
            content=ft.Column([goal_cal_input, goal_steps_input], tight=True),
            actions=[
                ft.TextButton("저장", on_click=save_goals),
                ft.TextButton("취소", on_click=close_goal_settings)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        page.overlay.append(goal_dialog)
        # ---------------------------------------------

        def on_save_meal(e):
            if app_state["current_date"].date() > datetime.now().date():
                show_snack_bar("미래 날짜는 기록할 수 없습니다.")
                return

            food = food_input.value
            try:
                amount = float(amount_input.value)
                if amount < 0: raise ValueError
            except ValueError:
                show_snack_bar("올바른 숫자를 입력해주세요")
                return

            cal_per_100, pro_per_100 = get_food_info(food)
            if cal_per_100 is None:
                show_snack_bar("음식 정보가 없습니다. 새로운 음식을 등록해주세요.")
                return

            calc_cal = (cal_per_100 / 100) * amount
            calc_pro = (pro_per_100 / 100) * amount

            with open(FILES["meal_log"], 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([get_current_date_str(), food, amount, calc_cal, calc_pro])

            food_input.value = ""
            amount_input.value = ""
            update_ui()
            show_snack_bar("식사가 기록되었습니다.")

        def on_save_steps(e):
            if app_state["current_date"].date() > datetime.now().date():
                show_snack_bar("미래 날짜는 기록할 수 없습니다.")
                return

            try:
                steps = int(steps_input.value)
                if steps < 0: raise ValueError
            except ValueError:
                show_snack_bar("올바른 숫자를 입력해주세요")
                return

            burned = steps * 0.03 
            
            with open(FILES["activity_log"], 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([get_current_date_str(), steps, burned])

            steps_input.value = ""
            update_ui()
            show_snack_bar("걷기가 기록되었습니다.")

        # 날짜 컨트롤 UI
        date_control_row = ft.Row([
            ft.ElevatedButton("< 이전", on_click=lambda e: change_date(e, -1)),
            ft.TextButton(content=date_text, on_click=open_date_picker),
            ft.ElevatedButton("다음 >", on_click=lambda e: change_date(e, 1)),
        ], alignment=ft.MainAxisAlignment.CENTER)

        page.add(
            date_control_row,
            ft.Text("※ 날짜를 클릭하면 달력이 열립니다.", size=12, color="grey"),
            ft.Divider(),
            ft.Text("누적 섭취 현황", size=20, weight="bold"),
            summary_text,
            ft.Divider(),
            
            # [신규 추가] 목표 달성률 텍스트와 목표 수정 버튼을 한 줄에 배치
            ft.Row([
                ft.Text("일일 목표 달성률", size=20, weight="bold"),
                ft.TextButton("목표 수정", icon="settings", on_click=open_goal_settings)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            ft.Row([progress_bar, rate_text], alignment=ft.MainAxisAlignment.CENTER),
            warning_text,
            ft.Divider(),
            ft.Text("식사 기록하기", size=18),
            ft.Row([food_input, amount_input, ft.ElevatedButton("저장", on_click=on_save_meal)]),
            ft.Divider(),
            ft.Text("걷기 기록하기", size=18),
            ft.Row([steps_input, ft.ElevatedButton("저장", on_click=on_save_steps)])
        )
        
        update_ui()

    except Exception as e:
        error_msg = traceback.format_exc()
        page.add(
            ft.Text("앱 실행 중 치명적인 오류가 발생했습니다!", color="red", weight="bold", size=20),
            ft.Text(error_msg, selectable=True)
        )
        print(error_msg)

ft.app(target=main)