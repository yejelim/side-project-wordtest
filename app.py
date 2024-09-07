import streamlit as st
import pandas as pd
import sqlite3

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
file_path = 'words.csv'  # CSV 파일 경로
words_df = pd.read_csv(file_path)

# 설정: 하루에 외울 단어 수
words_per_day = 20

# 학습 Day와 리뷰 Day를 선택하는 범위 확장
def generate_day_options(current_day):
    options = []
    review_week = 1
    for day in range(1, current_day + 1):
        options.append(f"Day {day}")
        if day % 5 == 0:
            options.append(f"Review Day-{review_week}주차")
            review_week += 1
    return options

# 사용자가 Day 또는 Review Day를 선택
current_day = st.session_state.day
day_options = generate_day_options(current_day)
selected_day = st.selectbox("학습할 Day를 선택하세요:", day_options)

# 선택된 Day가 리뷰 데이인지 확인
def is_review_day(selected_day):
    return "Review Day" in selected_day

# 리뷰 Day용 단어 인덱스 범위 계산 (이전 5일 동안 학습한 단어를 테스트)
def get_review_words_range(review_week, words_per_day):
    start_idx = (review_week - 1) * 5 * words_per_day
    end_idx = start_idx + 5 * words_per_day
    return start_idx, end_idx

# 오늘의 단어 계산 (리뷰 데이일 경우와 일반 학습 Day 구분)
if is_review_day(selected_day):
    # 리뷰 데이일 경우
    review_week = int(selected_day.split('-')[1].split('주차')[0])
    start_idx, end_idx = get_review_words_range(review_week, words_per_day)
    review_words_df = words_df.iloc[start_idx:end_idx]
    today_words = review_words_df.sample(frac=1).reset_index(drop=True)  # 랜덤으로 섞음
else:
    # 일반 학습 Day일 경우
    day = int(selected_day.split(' ')[1])
    start_idx, end_idx = (day - 1) * words_per_day, day * words_per_day
    today_words = words_df.iloc[start_idx:end_idx]

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

        user_answers[index] = st.text_input(f"{meaning}", key=f"word_{selected_day}_{index}")

    return user_answers

# 메인 프로그램
st.title("영어 단어 테스트 for 준혁")

if is_review_day(selected_day):
    st.write(f"오늘은 '{selected_day}'입니다! 이전 주차 동안 학습한 단어들을 복습하세요.")
else:
    st.write(f"오늘은 {selected_day}에 대한 학습입니다.")

if not today_words.empty:
    user_answers = run_test(today_words)

    if st.button("결과 확인"):
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
st.write("이전 학습 일자의 오답 노트를 확인하세요:")
days_with_notes = c.execute("SELECT DISTINCT day FROM incorrect_notes").fetchall()
for past_day in days_with_notes:
    if st.button(f"Day {past_day[0]} 오답 노트 보기"):
        incorrect_df = load_incorrect_answers(past_day[0])
        if incorrect_df is not None:
            st.write(incorrect_df)
        else:
            st.write(f"Day {past_day[0]}에 대한 오답 노트가 없습니다.")

conn.close()
