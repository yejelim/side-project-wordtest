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

# 사용자가 직접 Day를 선택
day = st.number_input("학습할 Day를 선택하세요:", min_value=1, max_value=100, value=st.session_state.day, step=1)

st.session_state.day = day

# CSV 파일 로드
file_path = 'words.csv'  # CSV 파일 경로
words_df = pd.read_csv(file_path)

# 설정: 하루에 외울 단어 수
words_per_day = 20

# 학습 일자에 따른 인덱스 범위 계산
def get_words_index(day, words_per_day):
    start_idx = (day - 1) * words_per_day
    end_idx = start_idx + words_per_day
    return start_idx, end_idx

# '리뷰 Day' 확인 (별도로 추가되는 리뷰 day)
def is_special_review_day():
    return st.session_state.get('special_day', False)

# 리뷰 Day용 단어 인덱스 범위 계산 (이전 5일 동안 학습한 단어를 테스트)
def get_review_words_range(day, words_per_day):
    start_idx, end_idx = get_words_index(day-4, words_per_day)
    return start_idx, end_idx + words_per_day * 5

# 오늘의 단어 인덱스 범위 계산
if is_special_review_day():
    # 리뷰 데이일 경우
    start_idx, end_idx = get_review_words_range(day, words_per_day)
    review_words_df = words_df.iloc[start_idx:end_idx]
    today_words = review_words_df.sample(frac=1).reset_index(drop=True)  # 랜덤으로 섞음
else:
    start_idx, end_idx = get_words_index(st.session_state.day, words_per_day)
    today_words = words_df.iloc[start_idx:end_idx]

# 복습용 단어 추가 (Day 2부터, 리뷰 day는 복습 제외)
def get_review_words(words, review_count=10):
    if f'review_words_day_{day}' not in st.session_state:
        st.session_state[f'review_words_day_{day}'] = words.sample(review_count).reset_index(drop=True)
    return st.session_state[f'review_words_day_{day}']

if day > 1 and not is_special_review_day():
    previous_day_words = words_df.iloc[get_words_index(day-1, words_per_day)[0]:get_words_index(day-1, words_per_day)[1]]
    review_words = get_review_words(previous_day_words)
    today_words = pd.concat([today_words, review_words]).reset_index(drop=True)

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

        user_answers[index] = st.text_input(f"{meaning}", key=f"word_{day}_{index}")

    return user_answers

# 메인 프로그램
st.title("영어 단어 테스트 for 준혁")

if is_special_review_day():
    st.write(f"오늘은 '리뷰 데이'입니다! 최근 5일 동안 학습한 단어들을 복습하세요.")
else:
    st.write(f"오늘은 Day {day}에 대한 학습입니다.")

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
            save_incorrect_answers(day, incorrect_answers)
        
        save_progress(day)

# 리뷰 데이 설정
if day % 5 == 0 and st.button("리뷰 데이 시작"):
    st.session_state.special_day = True
    st.experimental_rerun()

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
