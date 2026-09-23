import flet as ft
import csv
import traceback
from datetime import datetime, timedelta
from data_manager import init_files, get_food_info, calculate_daily_summary, FILES

def main(page: ft.Page):
    try:
        # --- 앱 기본 설정 및 테마 ---
        page.title = "핏 트래커 (FitTracker)"
        page.window_width = 450
        page.window_height = 750
        page.bgcolor = ft.Colors.BLUE_GREY_50 # 대문자 Colors 로 변경됨
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)

        # 데이터 저장용 CSV 파일들이 없으면 생성
        init_files()

        # 현재 화면에서 보고 있는 날짜를 저장하는 앱 상태
        app_state = {"current_date": datetime.now()}

        def get_current_date_str():
            # app_state의 날짜를 "YYYY-MM-DD" 문자열로 변환
            return app_state["current_date"].strftime("%Y-%m-%d")

        # --- UI 요소 초기화 ---
        date_text = ft.Text(value=get_current_date_str(), size=22, weight="bold")
        summary_text = ft.Text(size=16, weight="bold")
        progress_bar = ft.ProgressBar(width=300, height=20, value=0)
        rate_text = ft.Text(size=20, weight="bold")
        warning_text = ft.Text(color="red", visible=False)

        # 디자인이 적용된 입력창 (음식명 입력)
        food_input = ft.TextField(
            label="음식명 (예: 쌀밥)", 
            width=200, 
            prefix_icon=ft.Icons.RESTAURANT,
            border_radius=15, 
            filled=True, 
            bgcolor=ft.Colors.WHITE
        )
        # 디자인이 적용된 입력창 (걸음 수 입력)
        steps_input = ft.TextField(
            label="당일 걸음 수", 
            width=200, 
            prefix_icon=ft.Icons.DIRECTIONS_WALK, 
            border_radius=15,
            filled=True,
            bgcolor=ft.Colors.WHITE
        )

        # 음식 섭취량 배율(1인분 기준 몇 배 먹었는지)을 표시하는 텍스트
        multiplier_val = ft.Text(value="1.0", size=18, weight="bold")
        
        def minus_click(e):
            # 배율을 0.25씩 감소 (최소 0.25까지만 허용)
            val = float(multiplier_val.value)
            if val > 0.25: 
                multiplier_val.value = str(val - 0.25)
                page.update()

        def plus_click(e):
            # 배율을 0.25씩 증가
            val = float(multiplier_val.value)
            multiplier_val.value = str(val + 0.25)
            page.update()

        # +/- 버튼과 배율 텍스트를 가로로 배치한 스테퍼 UI
        stepper_row = ft.Row([
            ft.ElevatedButton("-", on_click=minus_click),
            multiplier_val,
            ft.ElevatedButton("+", on_click=plus_click),
            ft.Text("단위", color="grey", size=12)
        ], alignment=ft.MainAxisAlignment.START)

        # --- 이벤트 핸들러 ---
        def on_date_selected(e):
           # 달력에서 날짜를 선택했을 때 호출됨
           if date_picker.value:
                selected = date_picker.value
                # 시간대 보정 (UTC 기준으로 넘어오는 경우 한국 시간(+9)으로 조정)
                if selected.hour != 0:
                    selected += timedelta(hours=9)
                
                app_state["current_date"] = datetime(selected.year, selected.month, selected.day)
                update_ui()
                
        # 날짜 선택용 달력 위젯 설정
        date_picker = ft.DatePicker(
            on_change=on_date_selected,
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31)
        )
        page.overlay.append(date_picker)

        def open_date_picker(e):
            # 달력을 현재 선택된 날짜로 맞춰서 열기
            date_picker.value = app_state["current_date"]  
            date_picker.open = True
            page.update()

        def update_ui():
            # 현재 날짜의 요약 정보를 다시 계산해서 화면에 반영
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
            
            # 진행률 바는 0~1 사이 값으로 제한
            progress_bar.value = max(0.0, min(rate / 100.0, 1.0)) 

            # 목표 대비 80% 미만이거나 120% 이상이면 경고 표시
            if rate < 80 or rate >= 120:
                progress_bar.color = "red"
                rate_text.color = "red"
                warning_text.value = "안내: 금일 목표 열량에 미달/초과 하였습니다"
                warning_text.visible = True
            else:
                progress_bar.color = "teal"
                rate_text.color = "black"
                warning_text.visible = False

            page.update()

        def change_date(e, delta_days):
            # 이전/다음 날짜 버튼 클릭 시 날짜 이동
            app_state["current_date"] += timedelta(days=delta_days)
            update_ui()

        def show_snack_bar(message):
            # 화면 하단에 잠깐 뜨는 알림 메시지 표시
            snack = ft.SnackBar(ft.Text(message))
            page.overlay.append(snack)
            snack.open = True
            page.update()

        # 목표 설정 다이얼로그용 입력창
        goal_cal_input = ft.TextField(label="목표 섭취 열량(kcal)", width=200)
        goal_steps_input = ft.TextField(label="목표 걸음 수", width=200)

        def open_goal_settings(e):
            # 현재 저장된 목표값을 불러와서 다이얼로그에 채워 넣고 열기
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
            # 목표 설정 다이얼로그 닫기 (저장 안 함)
            goal_dialog.open = False
            page.update()

        def save_goals(e):
            # 입력값 유효성 검사 후 목표를 CSV에 저장
            try:
                new_cal = float(goal_cal_input.value)
                new_steps = int(goal_steps_input.value)
                if new_cal <= 0 or new_steps <= 0: raise ValueError
            except ValueError:
                show_snack_bar("올바른 양수(숫자)를 입력해주세요.")
                return
            
            with open(FILES["user_goal"], 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["target_calories", "target_steps"])
                writer.writerow([new_cal, new_steps])
            
            goal_dialog.open = False
            update_ui()
            show_snack_bar("목표가 성공적으로 수정되었습니다.")

        # 목표 설정용 다이얼로그 정의
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

        def on_save_meal(e):
            # 미래 날짜에는 식사 기록 불가
            if app_state["current_date"].date() > datetime.now().date():
                show_snack_bar("미래 날짜는 기록할 수 없습니다.")
                return

            food = food_input.value
            multiplier = float(multiplier_val.value)

            # 입력한 음식명으로 단위/칼로리/단백질 정보 조회
            unit_name, cal_per_unit, pro_per_unit = get_food_info(food)
            if unit_name is None:
                show_snack_bar("음식 정보가 없습니다.")
                return

            # 배율을 곱해 실제 섭취 칼로리/단백질 계산
            calc_cal = cal_per_unit * multiplier
            calc_pro = pro_per_unit * multiplier

            # 식사 기록을 CSV 파일에 추가
            with open(FILES["meal_log"], 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([get_current_date_str(), food, multiplier, calc_cal, calc_pro])

            # 입력창 초기화 후 화면 갱신
            food_input.value = ""
            multiplier_val.value = "1.0" 
            update_ui()
            show_snack_bar(f"{food} {multiplier}{unit_name} 식사가 기록되었습니다.") 

        def on_save_steps(e):
            # 미래 날짜에는 걸음 수 기록 불가
            if app_state["current_date"].date() > datetime.now().date():
                show_snack_bar("미래 날짜는 기록할 수 없습니다.")
                return

            try:
                steps = int(steps_input.value)
                if steps < 0: raise ValueError
            except ValueError:
                show_snack_bar("올바른 숫자를 입력해주세요")
                return

            # 걸음 수 기준 소모 칼로리 계산 (걸음당 0.03kcal)
            burned = steps * 0.03 

            # 활동 기록을 CSV 파일에 추가
            with open(FILES["activity_log"], 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([get_current_date_str(), steps, burned])

            steps_input.value = ""
            update_ui()
            show_snack_bar("걷기가 기록되었습니다.")

        # --- 화면 레이아웃 조립 ---

        # 날짜 이동 버튼 + 날짜 표시(클릭 시 달력 열림) 행
        date_control_row = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK_IOS, on_click=lambda e: change_date(e, -1)),
            ft.TextButton(content=date_text, on_click=open_date_picker),
            ft.IconButton(ft.Icons.ARROW_FORWARD_IOS, on_click=lambda e: change_date(e, 1)),
        ], alignment=ft.MainAxisAlignment.CENTER)

        # 1. 요약 카드 (오늘의 섭취/소비/목표 달성률 표시)
        summary_card = ft.Card(
            elevation=2,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.PIE_CHART, color=ft.Colors.TEAL),
                        ft.Text("오늘의 섭취 현황", size=18, weight="bold")
                    ]),
                    ft.Divider(color=ft.Colors.GREY_300),
                    summary_text,
                    ft.Container(height=10),
                    ft.Row([
                        ft.Text("목표 달성률", weight="bold"),
                        ft.TextButton("수정", icon=ft.Icons.EDIT, on_click=open_goal_settings)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([progress_bar, rate_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    warning_text
                ])
            )
        )

        # 2. 입력 카드 (음식/걸음 수 기록 입력)
        input_card = ft.Card(
            elevation=2,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.EDIT_DOCUMENT, color=ft.Colors.TEAL),
                        ft.Text("기록 추가하기", size=18, weight="bold")
                    ]),
                    ft.Divider(color=ft.Colors.GREY_300),
                    ft.Row([food_input, stepper_row]), 
                    ft.ElevatedButton(
                        "식사 저장", 
                        icon=ft.Icons.SAVE,
                        on_click=on_save_meal, 
                        width=300,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                    ),
                    ft.Container(height=10),
                    ft.Row([
                        steps_input, 
                        ft.ElevatedButton(
                            "저장", 
                            on_click=on_save_steps,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                        )
                    ])
                ])
            )
        )

        # 최종적으로 페이지에 위 요소들을 순서대로 추가
        page.add(
            date_control_row,
            ft.Row([ft.Text("※ 날짜를 클릭하면 달력이 열립니다.", size=12, color="grey")], alignment=ft.MainAxisAlignment.CENTER),
            summary_card,
            input_card
        )
        
        # 초기 화면 데이터 표시
        update_ui()

    except Exception as e:
        # 앱 실행 중 예외 발생 시 오류 메시지를 화면에 출력
        error_msg = traceback.format_exc()
        page.add(
            ft.Text("앱 실행 중 치명적인 오류가 발생했습니다!", color="red", weight="bold", size=20),
            ft.Text(error_msg, selectable=True)
        )
        print(error_msg)

if __name__ == "__main__":
    ft.app(target=main)