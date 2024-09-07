import streamlit as st
import pandas as pd
import sqlite3
import random

# SQLite 데이터베이스 설정
conn = sqlite3.connect('progress.db')
c = conn.cursor()

# 테이블 생성
c.execute('''
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY,
    last_day INTEGER
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS incorrect_notes (
    id INTEGER PRIMARY KEY,
    day INTEGER,
    meaning TEXT,
    user_answer TEXT,
    correct_answer TEXT
)
''')

conn.commit()

# 현재 학습 일자 설정
if 'day' not in st.session_state:
    c.execute("SELECT last_day FROM progress WHERE id = 1")
    result = c.fetchone()
    if result:
        st.session_state.day = result[0]
    else:
        st.session_state.day = 1
        c.execute("INSERT INTO progress (id, last_day) VALUES (1, ?)", (st.session_state.day,))
    conn.commit()

# CSV 파일 로드
file_path = 'words.csv'  # CSV 파일 경로 (2000개의 단어가 들어있는 파일)
words_df = pd.read_csv(file_path)

# 설정: 하루에 외울 단어 수
words_per_day = 20
max_day = 100  # 최대 학습일수 (2000개의 단어 기준)

# 학습 Day와 리뷰 Day를 선택하는 범위 확장 (100일 + 20주차까지 리뷰 데이)
def generate_day_options():
    options = []
    review_week = 1
    for day in range(1, max_day + 1):
        options.append(f"Day {day}")
        if day % 5 == 0:  # 5일마다 리뷰 데이 추가
            options.append(f"Review Day-{review_week}주차")
            review_week += 1
    return options

# 사용자가 Day 또는 Review Day를 선택
current_day = st.session_state.day
day_options = generate_day_options()
selected_day = st.selectbox("학습할 Day를 선택하세요:", day_options)

# 선택된 Day가 리뷰 데이인지 확인
def is_review_day(selected_day):
    return "Review Day" in selected_day

# 복습용 단어 추가 (이전 Day의 단어 중 10개를 고정)
def get_review_words_from_previous_day(day):
    if day <= 1:
        return pd.DataFrame()  # Day 1일 경우 전날이 없으므로 빈 데이터프레임 반환

    if f'review_words_day_{day}' not in st.session_state:
        # 전날 단어 20개 중 10개를 랜덤으로 선택
        start_idx, end_idx = (day - 2) * words_per_day, (day - 1) * words_per_day
        previous_day_words = words_df.iloc[start_idx:end_idx]
        selected_review_words = previous_day_words.sample(n=10).reset_index(drop=True)
        st.session_state[f'review_words_day_{day}'] = selected_review_words
    return st.session_state[f'review_words_day_{day}']

# 리뷰 Day용 단어 인덱스 범위 계산 (이전 5일 동안 학습한 단어를 테스트)
def get_review_words_range(review_week, words_per_day):
    start_idx = (review_week - 1) * 5 * words_per_day
    end_idx = start_idx + 5 * words_per_day
    return start_idx, end_idx

# 오늘의 단어 계산 (리뷰 데이일 경우와 일반 학습 Day 구분)
if is_review_day(selected_day):
    # 리뷰 데이일 경우
    review_week = int(selected_day.split('-')[1].split('주차')[0])

    # 리뷰 Day에 해당하는 단어가 세션 상태에 없다면 저장
    if f'review_words_week_{review_week}' not in st.session_state:
        start_idx, end_idx = get_review_words_range(review_week, words_per_day)
        review_words_df = words_df.iloc[start_idx:end_idx]
        st.session_state[f'review_words_week_{review_week}'] = review_words_df.sample(frac=1).reset_index(drop=True)
    
    # 세션에서 고정된 단어 목록 불러오기
    today_words = st.session_state[f'review_words_week_{review_week}']

else:
    # 일반 학습 Day일 경우
    day = int(selected_day.split(' ')[1])
    start_idx, end_idx = (day - 1) * words_per_day, day * words_per_day
    today_words = words_df.iloc[start_idx:end_idx]

    # 이전 Day의 20개 중 10개의 복습 단어 추가
    previous_day_review_words = get_review_words_from_previous_day(day)
    today_words = pd.concat([today_words, previous_day_review_words]).reset_index(drop=True)

# 오답 노트 저장
def save_incorrect_answers(day, incorrect_answers):
    for meaning, user_answer, correct_word in incorrect_answers:
        c.execute('''
            INSERT INTO incorrect_notes (day, meaning, user_answer, correct_answer)
            VALUES (?, ?, ?, ?)
        ''', (day, meaning, user_answer, correct_word))
    conn.commit()

# 오답 노트 로드
def load_incorrect_answers(day):
    c.execute("SELECT meaning, user_answer, correct_answer FROM incorrect_notes WHERE day = ?", (day,))
    result = c.fetchall()
    if result:
        return pd.DataFrame(result, columns=['Meaning', 'Your Answer', 'Correct Answer'])
    else:
        return None

# 성취도 기록 저장
def save_progress(day):
    c.execute('''
        UPDATE progress
        SET last_day = ?
        WHERE id = 1
    ''', (day,))
    conn.commit()

# 테스트 실행
def run_test(words):
    score = 0
    incorrect_answers = []
    user_answers = {}

    for index, row in words.iterrows():
        meaning = row['meaning']
        correct_word = row['word']

        # 고유한 key 값으로 입력 필드 생성
        user_answers[index] = st.text_input(f"{meaning}", key=f"{selected_day}_word_{index}")

    return user_answers

# 메인 프로그램
st.title("영어 단어 테스트 for 준혁")

if is_review_day(selected_day):
    st.write(f"오늘은 '{selected_day}'입니다! 이전 주차 동안 학습한 단어들을 복습하세요.")
else:
    st.write(f"오늘은 {selected_day}에 대한 학습입니다.")

if not today_words.empty:
    user_answers = run_test(today_words)

    # 고유한 key 값을 가진 버튼 생성
    if st.button(f"{selected_day} 결과 확인"):
        score = 0
        incorrect_answers = []
        for index, row in today_words.iterrows():
            meaning = row['meaning']
            correct_word = row['word']
            user_answer = user_answers[index]

            if user_answer.lower() == correct_word.lower():
                score += 1
            else:
                incorrect_answers.append((meaning, user_answer, correct_word))

        # 결과 표시
        total = len(today_words)
        st.write(f"총 {total} 문제 중 {score} 문제 맞췄습니다.")
        
        if incorrect_answers:
            st.write("오답 노트:")
            for meaning, user_answer, correct_word in incorrect_answers:
                st.write(f"{meaning}: 당신의 답변 - '{user_answer}', 정답 - '{correct_word}'")
            save_incorrect_answers(selected_day, incorrect_answers)
        
        save_progress(current_day)

# 오답 노트 열람
st.write(f"{selected_day} 오답 노트를 확인하세요:")
incorrect_df = load_incorrect_answers(selected_day)
if incorrect_df is not None:
    st.write(incorrect_df)
else:
    st.write(f"{selected_day}에 대한 오답 노트가 없습니다.")

conn.close()
